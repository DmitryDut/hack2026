"""End-to-end smoke test of the demo path (docs/demo-script.md, part 1)."""

from tests.conftest import login_as

SVC = "/cabinet/services/svc-vcs"
NBSP = " "


def post(client, url, **data):
    return client.post(url, data=data, follow_redirects=True)


def test_login_and_isolation(client):
    assert client.get("/cabinet", follow_redirects=False).status_code == 303
    bad = client.post("/login", data={"login": "mts-link-1", "password": "x"})
    assert bad.status_code == 401 and "Неверный логин или пароль" in bad.text
    login_as(client)
    assert "Link ВКС" in client.get("/cabinet").text
    other = login_as(client, "other-partner")
    assert other.get(SVC).status_code == 404


def test_signature_validation(client):
    login_as(client)
    url = f"{SVC}/signatures"
    r = post(client, url, ipv4="10.10.2.10", uri="api.mts-link.ru", port="70000", protocol="HTTPS")
    assert r.status_code == 422 and "Порт должен быть от 1 до 65535" in r.text
    r = post(client, url, ipv4="10.10.2.10", uri="a.ru", port="8443", protocol="SMTP")
    assert r.status_code == 422 and "Недопустимый протокол" in r.text
    ok = post(client, url, ipv4="10.10.2.10", uri="api.mts-link.ru", port="8443", protocol="HTTPS")
    assert ok.status_code == 200 and "Сигнатура добавлена" in ok.text
    dup = post(client, url, ipv4="10.10.2.10", uri="api.mts-link.ru", port="8443", protocol="HTTPS")
    assert dup.status_code == 422 and "уже есть" in dup.text


def test_pricing_follows_tariff_and_duration(client):
    login_as(client)
    r = post(client, f"{SVC}/tariff", tariff_code="PLATINUM", duration_code="12H")
    assert f"30{NBSP}000" in client.get(f"{SVC}?tab=tariff").text
    assert r.status_code == 200
    post(client, f"{SVC}/tariff", tariff_code="PLATINUM", duration_code="24H")
    assert f"51{NBSP}000" in client.get(f"{SVC}?tab=tariff").text
    post(client, f"{SVC}/tariff", tariff_code="GOLD", duration_code="12H")
    assert f"10{NBSP}000" in client.get(f"{SVC}?tab=tariff").text


def test_full_demo_path(client):
    login_as(client)
    # tariff and price
    post(client, f"{SVC}/tariff", tariff_code="PLATINUM", duration_code="12H")
    assert "Тестирование" in client.get(f"{SVC}?tab=test").text
    assert (
        "Начать тест" not in client.get(f"{SVC}?tab=test").text
    )  # locked until price is confirmed
    post(client, f"{SVC}/confirm-price")
    # test run: sig-4 fails
    post(client, f"{SVC}/test/start")
    for sig in ("sig-1", "sig-2", "sig-3"):
        post(client, f"{SVC}/test/check/{sig}")
        post(client, f"{SVC}/test/confirm/{sig}")
    failed = post(client, f"{SVC}/test/check/sig-4")
    assert "RTP-поток не отвечает" in failed.text and "Тест не пройден" in failed.text
    # back, fix the port, run again
    post(client, f"{SVC}/test/back")
    fix = post(
        client,
        f"{SVC}/signatures/sig-4",
        ipv4="10.10.1.8",
        uri="media2.mts-link.ru",
        port="5006",
        protocol="RTP",
    )
    assert "Сигнатура изменена" in fix.text
    post(client, f"{SVC}/test/start")
    for sig in ("sig-1", "sig-2", "sig-3", "sig-4"):
        post(client, f"{SVC}/test/check/{sig}")
        r = post(client, f"{SVC}/test/confirm/{sig}")
    assert "Тест пройден" in r.text
    # activation and priority indicator
    applied = post(client, f"{SVC}/apply")
    assert "Приоритет включён" in applied.text
    assert "Трафик приоритизирован" in client.get(SVC + "?tab=launch").text
    dash = client.get("/cabinet").text
    assert "Трафик приоритизирован" in dash and "1 из 2" in dash
    # locked after activation
    locked = post(client, f"{SVC}/signatures/sig-1/delete")
    assert "изменения запрещены" in locked.text
    # the priority panel shows what is under priority
    panel = client.get(SVC + "?tab=launch").text
    assert "10.10.1.8:5006" in panel and "Сигнатур под приоритетом" not in panel
    assert "Сигнатур под приоритетом" in client.get("/cabinet").text
    # operator sees the journal and can reset
    login_as(client, "operator")
    journal = client.get("/operator/journal").text
    assert "applied_to_production" in journal and "gsma_session" in journal
    reset = post(client, "/operator/services/svc-vcs/reset")
    assert "сброшена в черновик" in reset.text
