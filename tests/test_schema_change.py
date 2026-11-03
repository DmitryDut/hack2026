"""Change scenarios C-01…C-04 (docs/scenarios.md §4): through the UI, no code or restart."""

import json

from tests.conftest import login_as

NBSP = " "
SVC = "/cabinet/services/svc-vcs"


def save_schema(client, type_, mutate):
    page = client.get(f"/admin/schemas?type={type_}").text
    start = page.index('spellcheck="false"') + len('spellcheck="false"')
    text = page[page.index(">", start) + 1 : page.index("</textarea>")]
    import html

    schema = json.loads(html.unescape(text))
    mutate(schema)
    return client.post(f"/admin/schemas/{type_}", data={"schema_text": json.dumps(schema)})


def test_c01_new_tariff_is_priced_and_offered(client):
    login_as(client, "operator")
    r = client.post(
        "/entities/tariff",
        data={
            "code": "DIAMOND_PLUS",
            "name": "Бриллиант+",
            "bitrate_mbps": "300",
            "priority_level": "5",
            "price_multiplier": "5",
            "sla_percent": "99.99",
        },
    )
    assert r.status_code == 200 and "Запись добавлена" in r.text
    bad = client.post("/entities/tariff", data={"code": "x", "name": "", "bitrate_mbps": "abc"})
    assert bad.status_code == 422
    login_as(client)
    client.post(f"{SVC}/tariff", data={"tariff_code": "DIAMOND_PLUS"})
    page = client.get(f"{SVC}?tab=tariff").text
    assert "Бриллиант+" in page and f"150{NBSP}000" in page


def test_c02_signature_gets_ipv6_and_optional_uri(client):
    login_as(client, "operator")

    def mutate(schema):
        schema["properties"]["ipv6"] = {"type": "string", "title": "IPv6", "format": "ipv6"}
        schema["required"].remove("uri")

    assert "Схема сохранена" in save_schema(client, "signature", mutate).text
    login_as(client)
    page = client.get(f"{SVC}?tab=data").text
    assert "IPv6" in page and "vcs.mts-link.ru" in page  # old rows still render
    ok = client.post(
        f"{SVC}/signatures",
        data={"ipv4": "10.10.9.9", "ipv6": "::1", "port": "8443", "protocol": "TCP"},
    )
    assert "Сигнатура добавлена" in ok.text and "::1" in ok.text
    bad = client.post(
        f"{SVC}/signatures",
        data={"ipv4": "10.10.9.8", "ipv6": "nope", "port": "8443", "protocol": "TCP"},
    )
    assert bad.status_code == 422 and "Неверный формат" in bad.text


def test_c03_service_gets_sla_field_with_range(client):
    login_as(client, "operator")

    def mutate(schema):
        schema["properties"]["sla_percent"] = {
            "type": "number",
            "title": "SLA, %",
            "minimum": 99,
            "maximum": 99.999,
        }

    save_schema(client, "service", mutate)
    login_as(client)
    assert "SLA, %" in client.get(f"{SVC}?tab=data").text
    ok = client.post(
        f"{SVC}/params", data={"name": "Link ВКС", "description": "x", "sla_percent": "99.5"}
    )
    assert "Параметры услуги сохранены" in ok.text
    bad = client.post(f"{SVC}/params", data={"name": "Link ВКС", "sla_percent": "50"})
    assert bad.status_code == 422 and "не меньше 99" in bad.text


def test_c04_new_entity_type_from_admin(client):
    login_as(client, "operator")
    assert (
        "Тип создан"
        in client.post("/admin/schemas", data={"type_id": "monitoring", "title": "Мониторинг"}).text
    )

    def mutate(schema):
        schema["properties"] = {
            "endpoint": {"type": "string", "title": "Endpoint"},
            "interval_sec": {"type": "integer", "title": "Интервал, сек", "minimum": 10},
        }
        schema["required"] = ["endpoint"]

    save_schema(client, "monitoring", mutate)
    page = client.get("/entities/monitoring").text
    assert "Мониторинг" in page and "Endpoint" in page and "Интервал, сек" in page
    ok = client.post(
        "/entities/monitoring",
        data={"endpoint": "https://mon.example.ru/health", "interval_sec": "30"},
    )
    assert "Запись добавлена" in ok.text and "mon.example.ru" in ok.text
    bad = client.post("/entities/monitoring", data={"endpoint": "x", "interval_sec": "5"})
    assert bad.status_code == 422 and "не меньше 10" in bad.text


def test_schema_editor_rejects_broken_and_core_changes(client):
    login_as(client, "operator")
    broken = client.post(
        "/admin/schemas/signature", data={"schema_text": '{"properties": "not-an-object"}'}
    )
    assert broken.status_code == 422
    garbage = client.post("/admin/schemas/signature", data={"schema_text": "{oops"})
    assert garbage.status_code == 422 and "Некорректный JSON" in garbage.text

    def drop_port(schema):
        del schema["properties"]["port"]
        schema["required"].remove("port")

    dropped = save_schema(client, "signature", drop_port)
    assert dropped.status_code == 422 and "Нельзя удалить базовое поле" in dropped.text
    login_as(client)
    assert "Порт" in client.get(f"{SVC}?tab=data").text  # schema was not changed
