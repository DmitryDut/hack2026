"""P1.7: tab gates from process.yaml (C-06) and the JSON for PX from px_payload.yaml (C-07)."""

import copy

import pytest

from app.services import config
from tests.conftest import login_as

SVC = "/cabinet/services/svc-vcs"


@pytest.fixture
def override(monkeypatch):
    """Replace a YAML config in memory: override('process', lambda cfg: ...)."""
    original = config.load

    def apply(name, mutate):
        def patched(requested):
            data = copy.deepcopy(original(requested))
            if requested == name:
                mutate(data)
            return data

        monkeypatch.setattr(config, "load", patched)

    return apply


def test_export_has_only_confirmed_services(client):
    login_as(client)
    empty = client.get("/api/v1/partners/mts-link-1/export").json()
    assert empty["partner_id"] == "mts-link-1" and empty["services"] == []
    client.post(f"{SVC}/tariff", data={"tariff_code": "PLATINUM"})
    client.post(f"{SVC}/confirm-price")
    data = client.get("/api/v1/partners/mts-link-1/export").json()
    assert data["schema_version"] == "0.1" and data["partner_name"] == "MTS Link"
    (service,) = data["services"]
    assert service["name"] == "Link ВКС" and len(service["signatures"]) == 4
    assert service["qos_profile"] == {
        "code": "PLATINUM",
        "name": "Платина",
        "bitrate_mbps": 100,
        "latency_ms": 30,
        "priority_level": 4,
        "sla_percent": 99.95,
    }
    assert "duration" not in service
    assert "JSON для PX" in client.get("/cabinet/export").text


def test_export_is_isolated_between_partners(client):
    login_as(client, "other-partner")
    assert client.get("/api/v1/partners/mts-link-1/export").status_code == 404


def test_c07_new_field_in_px_json_by_config_only(client, override):
    login_as(client)
    client.post(f"{SVC}/tariff", data={"tariff_code": "GOLD"})
    client.post(f"{SVC}/confirm-price")
    before = client.get("/api/v1/partners/mts-link-1/export").json()["services"][0]
    assert "status" not in before["qos_profile"]
    override(
        "px_payload",
        lambda cfg: cfg["service"]["lookups"]["qos_profile"]["fields"].append("status"),
    )
    after = client.get("/api/v1/partners/mts-link-1/export").json()["services"][0]
    assert after["qos_profile"]["status"] == "ACTIVE"


def test_c06_test_before_price_by_config_only(client, override):
    login_as(client)
    # default: the test tab is closed until the price is confirmed
    assert "Начать тест" not in client.get(f"{SVC}?tab=test").text

    def mutate(cfg):
        cfg["gates"]["test"] = ["has_signatures"]
        cfg["gates"]["launch"] = ["test_passed", "price_confirmed"]

    override("process", mutate)
    assert "Начать тест" in client.get(f"{SVC}?tab=test").text
    client.post(f"{SVC}/test/start")
    for sig in ("sig-1", "sig-2", "sig-3"):
        client.post(f"{SVC}/test/check/{sig}")
        client.post(f"{SVC}/test/confirm/{sig}")
    client.post(
        f"{SVC}/signatures/sig-4",
        data={"ipv4": "10.10.1.8", "uri": "media2.mts-link.ru", "port": "5006", "protocol": "RTP"},
    )
    client.post(f"{SVC}/test/start")
    for sig in ("sig-1", "sig-2", "sig-3", "sig-4"):
        client.post(f"{SVC}/test/check/{sig}")
        client.post(f"{SVC}/test/confirm/{sig}")
    # price still unconfirmed, so activation is refused with the gate message
    refused = client.post(f"{SVC}/apply")
    assert "Сначала подтвердите цену" in refused.text
    client.post(f"{SVC}/tariff", data={"tariff_code": "PLATINUM"})
    client.post(f"{SVC}/confirm-price")
    # changing the tariff reset the run; the full path works again once the test is repeated
    assert "Начать тест" in client.get(f"{SVC}?tab=test").text


def test_c06_tab_order_and_titles_from_config(client, override):
    login_as(client)

    def mutate(cfg):
        cfg["tabs"] = [cfg["tabs"][1], cfg["tabs"][0], *cfg["tabs"][2:]]
        cfg["tabs"][0]["title"] = "Тариф"

    override("process", mutate)
    page = client.get(SVC).text
    assert page.index("Тариф<") < page.index("Данные услуги")
