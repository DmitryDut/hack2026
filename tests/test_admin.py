"""P5: administration section — tariffs and gradations, durations, traffic passport editor."""

from tests.conftest import login_as

SVC = "/cabinet/services/svc-vcs"
NBSP = " "


def operator(client):
    return login_as(client, "operator")


def test_admin_hub_and_pages_for_operator_only(client):
    login_as(client)
    assert client.get("/admin", follow_redirects=False).status_code == 303
    operator(client)
    hub = client.get("/admin").text
    for text in (
        "Градации и тарифы",
        "Сроки и коэффициенты",
        "Параметры идентификации трафика",
        "Поля услуги",
    ):
        assert text in hub
    for path in ("/admin/tariffs", "/admin/durations", "/admin/passport", "/admin/service-fields"):
        assert client.get(path).status_code == 200, path
    assert "Администрирование" in client.get("/admin/tariffs").text


def test_tariff_levels_add_hide_delete_and_price_matrix(client):
    operator(client)
    page = client.get("/admin/tariffs").text
    assert "Платина" in page and f"30{NBSP}000" in page  # matrix: Platinum, 12 h
    add = client.post(
        "/admin/data/tariff",
        data={
            "code": "TITAN",
            "name": "Титан",
            "bitrate_mbps": "400",
            "priority_level": "6",
            "price_multiplier": "6",
            "sla_percent": "99.99",
            "latency_ms": "10",
        },
    )
    assert "Запись добавлена" in add.text and f"240{NBSP}000" in add.text  # 400 × 100 × 6 × 1.0
    bad = client.post("/admin/data/tariff", data={"code": "t", "name": ""})
    assert bad.status_code == 422
    edit = client.post(
        "/admin/data/tariff/TITAN",
        data={
            "name": "Титан+",
            "bitrate_mbps": "500",
            "priority_level": "6",
            "price_multiplier": "6",
            "sla_percent": "99.99",
            "latency_ms": "8",
            "status": "ACTIVE",
        },
    )
    assert "Изменения сохранены" in edit.text and "Титан+" in edit.text
    login_as(client)
    assert "Титан+" in client.get(f"{SVC}?tab=tariff").text
    operator(client)
    assert "Тариф скрыт" in client.post("/admin/data/tariff/TITAN/toggle").text
    login_as(client)
    assert "Титан+" not in client.get(f"{SVC}?tab=tariff").text
    operator(client)
    assert "Запись удалена" in client.post("/admin/data/tariff/TITAN/delete").text


def test_used_tariff_cannot_be_deleted(client):
    login_as(client)
    client.post(f"{SVC}/tariff", data={"tariff_code": "GOLD", "duration_code": "12H"})
    operator(client)
    assert "используется в услугах" in client.post("/admin/data/tariff/GOLD/delete").text.lower()


def test_duration_coefficients_change_prices(client):
    operator(client)
    r = client.post(
        "/admin/data/duration", data={"code": "48H", "hours": "48", "price_multiplier": "2.5"}
    )
    assert "Запись добавлена" in r.text
    changed = client.post("/admin/data/duration/48H", data={"hours": "48", "price_multiplier": "3"})
    assert "Изменения сохранены" in changed.text
    assert f"90{NBSP}000" in client.get("/admin/tariffs").text  # Platinum 100 × 100 × 3.0 × 3.0


def test_passport_editor_adds_changes_and_deletes_fields(client):
    operator(client)
    add = client.post(
        "/admin/fields/signature",
        data={
            "name": "ipv6",
            "title": "IPv6",
            "type": "string",
            "format": "ipv6",
            "required": "on",
        },
    )
    assert "Поле добавлено" in add.text
    login_as(client)
    form = client.get(f"{SVC}?tab=data").text
    assert "IPv6" in form
    miss = client.post(
        f"{SVC}/signatures",
        data={"ipv4": "10.10.9.9", "uri": "x.ru", "port": "443", "protocol": "TCP"},
    )
    assert miss.status_code == 422 and "Обязательное поле" in miss.text
    ok = client.post(
        f"{SVC}/signatures",
        data={"ipv4": "10.10.9.9", "uri": "x.ru", "port": "443", "protocol": "TCP", "ipv6": "::1"},
    )
    assert "Сигнатура добавлена" in ok.text
    operator(client)
    assert (
        "Поле сохранено"
        in client.post(
            "/admin/fields/signature/ipv6", data={"title": "IPv6-адрес", "format": "ipv6"}
        ).text
    )
    assert "Базовое поле удалить нельзя" in client.post("/admin/fields/signature/port/delete").text
    assert "Поле удалено" in client.post("/admin/fields/signature/ipv6/delete").text
    login_as(client)
    assert "IPv6" not in client.get(f"{SVC}?tab=data").text


def test_passport_editor_validates_input(client):
    operator(client)
    assert (
        "Идентификатор поля"
        in client.post(
            "/admin/fields/signature", data={"name": "Bad Name", "title": "x", "type": "string"}
        ).text
    )
    assert (
        "уже есть"
        in client.post(
            "/admin/fields/signature", data={"name": "port", "title": "x", "type": "integer"}
        ).text
    )
    ranged = client.post(
        "/admin/fields/service",
        data={
            "name": "sla_percent",
            "title": "SLA, %",
            "type": "number",
            "minimum": "99",
            "maximum": "99.999",
        },
    )
    assert "Поле добавлено" in ranged.text
    login_as(client)
    assert (
        "не меньше 99"
        in client.post(f"{SVC}/params", data={"name": "Link ВКС", "sla_percent": "50"}).text
    )
