"""P4/P6: price = Мбит/с × ставка × коэффициент тарифа (₽ в месяц); C-05 changes it by config."""

import copy

from sqlmodel import Session

from app.db import engine
from app.models import Tariff
from app.services import config, pricing
from tests.conftest import login_as

NBSP = " "
SVC = "/cabinet/services/svc-vcs"


def price(code):
    with Session(engine) as db:
        return pricing.price(db.get(Tariff, code))


def test_prices_follow_the_task_formula(client):
    assert price("BRONZE") == 1000
    assert price("SILVER") == 4500
    assert price("GOLD") == 10000
    assert price("PLATINUM") == 30000
    assert price("DIAMOND") == 80000


def test_c05_rate_by_config_and_tariff_coefficient_by_data(client, monkeypatch):
    original = config.load

    def patched(name):
        data = copy.deepcopy(original(name))
        if name == "pricing":
            data["factors"][1]["const"] = 120
        return data

    monkeypatch.setattr(config, "load", patched)
    assert price("PLATINUM") == 36000
    monkeypatch.setattr(config, "load", original)
    login_as(client, "operator")
    client.post(
        "/admin/data/tariff/GOLD",
        data={
            "name": "Золото",
            "bitrate_mbps": "50",
            "priority_level": "3",
            "price_multiplier": "1.5",
            "sla_percent": "99.9",
            "latency_ms": "50",
            "status": "ACTIVE",
        },
    )
    assert price("GOLD") == 7500


def test_tariff_change_resets_price_confirmation(client):
    login_as(client)
    client.post(f"{SVC}/tariff", data={"tariff_code": "GOLD"})
    assert "Цена подтверждена" in client.post(f"{SVC}/confirm-price").text
    client.post(f"{SVC}/tariff", data={"tariff_code": "SILVER"})
    page = client.get(f"{SVC}?tab=tariff").text
    assert "Подтвердить цену" in page and f"4{NBSP}500" in page
