"""P4: price = Мбит/с × ставка × коэф. тарифа × коэф. срока; C-05 changes it by config only."""

import copy

from app.models import Duration, Tariff
from app.services import config, pricing
from tests.conftest import login_as

NBSP = " "


def price(db_client, tariff, duration):
    from sqlmodel import Session

    from app.db import engine

    with Session(engine) as db:
        return pricing.price(db.get(Tariff, tariff), db.get(Duration, duration))


def test_prices_follow_the_task_formula(client):
    assert price(client, "PLATINUM", "12H") == 30000
    assert price(client, "GOLD", "12H") == 10000
    assert price(client, "GOLD", "24H") == 17000
    assert price(client, "SILVER", "12H") == 4500
    assert price(client, "DIAMOND", "12H") == 80000
    assert price(client, "PLATINUM", "1H") == 4500


def test_c05_rate_and_duration_discount_by_config_and_data(client, monkeypatch):
    original = config.load

    def patched(name):
        data = copy.deepcopy(original(name))
        if name == "pricing":
            data["factors"][1]["const"] = 120
        return data

    monkeypatch.setattr(config, "load", patched)
    assert price(client, "PLATINUM", "12H") == 36000
    monkeypatch.setattr(config, "load", original)
    login_as(client, "operator")
    client.post(
        "/entities/duration/24H", data={"code": "24H", "hours": "24", "price_multiplier": "1.5"}
    )
    assert price(client, "GOLD", "24H") == 15000


def test_tariff_change_resets_price_confirmation(client):
    login_as(client)
    svc = "/cabinet/services/svc-vcs"
    client.post(f"{svc}/tariff", data={"tariff_code": "GOLD", "duration_code": "12H"})
    assert "Цена подтверждена" in client.post(f"{svc}/confirm-price").text
    client.post(f"{svc}/tariff", data={"tariff_code": "SILVER", "duration_code": "12H"})
    assert "Подтвердить цену" in client.get(f"{svc}?tab=tariff").text
    assert f"4{NBSP}500" in client.get(f"{svc}?tab=tariff").text
