"""P2: PX storefront, signed embed token, CSP, PX / catalog mocks, offer variants."""

import time

from app.services import auth
from tests.conftest import login_as

SVC = "/cabinet/services/svc-vcs"
NBSP = " "


def token(payload=None, secret=None):
    payload = payload or {
        "login": "mts-link-1",
        "role": "partner",
        "name": "MTS Link",
        "partner_id": "mts-link-1",
        "exp": int(time.time()) + 600,
    }
    if secret is None:
        return auth.make_token(payload)
    old, auth.SECRET = auth.SECRET, secret
    try:
        return auth.make_token(payload)
    finally:
        auth.SECRET = old


def test_embed_accepts_valid_token_and_opens_cabinet(client):
    r = client.get(f"/embed?token={token()}", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/cabinet"
    page = client.get("/cabinet").text
    assert "Link ВКС" in page and 'class="embedded"' in page
    assert "frame-ancestors 'self'" in client.get("/cabinet").headers["content-security-policy"]


def test_embed_tab_mode_has_site_header(client):
    client.get(f"/embed?token={token()}&mode=tab")
    assert 'class="embedded"' not in client.get("/cabinet").text


def test_embed_rejects_bad_tokens(client):
    cases = {
        "garbage.token": "подпись не сошлась",
        "garbage": "неверный формат",
        "": "неверный формат",
        token({"partner_id": "mts-link-1", "role": "partner", "exp": 1000000000}): "срок действия",
        token(secret="wrong-secret"): "подпись не сошлась",
    }
    for bad, reason in cases.items():
        r = client.get(f"/embed?token={bad}", follow_redirects=False)
        assert r.status_code == 401 and reason in r.text, bad
    assert (
        client.get("/cabinet", follow_redirects=False).status_code == 303
    )  # no session was created


def test_showcase_embeds_the_cabinet_by_token(client):
    page = client.get("/px-showcase").text
    assert "Конфигурировать сервисы QoS" in page and "/embed?token=" in page
    assert "other-partner" in client.get("/px-showcase?partner=other-partner").text


def test_catalog_and_px_mocks(client):
    catalog = client.get("/rc/qos_catalog").json()
    assert {p["code"] for p in catalog["profiles"]} >= {"GOLD", "PLATINUM"} and "HTTPS" in catalog[
        "protocols"
    ]
    reg = client.post(
        "/px/reg", json={"company": "Новая", "contact": "a@b.ru", "traffic": "video"}
    ).json()
    assert reg == {"id": "partners-1"}
    saved = client.post("/px/save_qos", json={"client_id": "partners-1", "profile": "GOLD"}).json()
    assert saved == {"id": "qos_profiles-1"}
    priced = client.post(
        "/px/price",
        json={
            "partner_id": "x",
            "services": [
                {"service_id": "s", "qos_profile": {"code": "GOLD"}, "duration": {"code": "12H"}}
            ],
        },
    ).json()
    assert priced["total_price_rub_per_month"] == 10000


def test_offer_variants_compare_and_apply(client):
    login_as(client)
    client.post(f"{SVC}/tariff", data={"tariff_code": "PLATINUM", "duration_code": "12H"})
    client.post(
        "/cabinet/services/svc-chat/tariff", data={"tariff_code": "GOLD", "duration_code": "24H"}
    )
    assert f"47{NBSP}000" in client.get("/cabinet/offer").text
    saved = client.post("/cabinet/offer/variants", data={"name": "Базовый"})
    assert "Вариант сохранён" in saved.text
    client.post(f"{SVC}/tariff", data={"tariff_code": "SILVER", "duration_code": "12H"})
    page = client.get("/cabinet/offer").text
    assert "Базовый" in page and f"21{NBSP}500" in page  # current 4 500 + 17 000
    applied = client.post("/cabinet/offer/variants/1/apply")
    assert (
        "Вариант применён" in applied.text and f"47{NBSP}000" in client.get("/cabinet/offer").text
    )
    assert "Укажите название" in client.post("/cabinet/offer/variants", data={"name": " "}).text
    other = login_as(client, "other-partner")
    assert other.post("/cabinet/offer/variants/1/delete").status_code == 404
