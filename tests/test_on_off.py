"""P6: the service is either switched on or off — no hours anywhere."""

import re

from sqlmodel import Session, select

from app.db import engine
from app.models import EventLog
from tests.conftest import login_as

SVC = "/cabinet/services/svc-vcs"


def pass_test(client):
    login_as(client)
    client.post(f"{SVC}/tariff", data={"tariff_code": "PLATINUM"})
    client.post(f"{SVC}/confirm-price")
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


def events():
    with Session(engine) as db:
        return [e.event for e in db.exec(select(EventLog).order_by(EventLog.id))]


def test_switch_on_off_and_on_again(client):
    pass_test(client)
    on = client.post(f"{SVC}/apply")
    assert "Приоритет включён" in on.text and "Выключить приоритет" in on.text
    first = re.search(r"qod-session-[0-9a-f]{6}", client.get(f"{SVC}?tab=launch").text).group(0)
    assert "Трафик приоритизирован" in client.get("/cabinet").text
    off = client.post(f"{SVC}/disable")
    assert "Приоритет выключен" in off.text
    launch = client.get(f"{SVC}?tab=launch").text
    assert "Включить приоритет" in launch and "Выключить приоритет" not in launch
    assert "Приоритет пока не включён" in client.get("/cabinet").text
    again = client.post(f"{SVC}/apply")
    assert "Приоритет включён" in again.text
    second = re.search(r"qod-session-[0-9a-f]{6}", client.get(f"{SVC}?tab=launch").text).group(0)
    assert first != second
    assert events().count("applied_to_production") == 2 and "priority_disabled" in events()


def test_disable_requires_enabled_service(client):
    login_as(client)
    assert "Приоритет не включён" in client.post(f"{SVC}/disable").text


def test_enabled_service_is_locked_disabled_one_is_editable(client):
    pass_test(client)
    client.post(f"{SVC}/apply")
    assert "изменения запрещены" in client.post(f"{SVC}/tariff", data={"tariff_code": "GOLD"}).text
    client.post(f"{SVC}/disable")
    changed = client.post(f"{SVC}/tariff", data={"tariff_code": "GOLD"})
    assert "Тариф выбран" in changed.text
    # the change reset the test and the price confirmation, so the test tab is closed again
    assert "Начать тест" not in client.get(f"{SVC}?tab=test").text
    assert "Подтвердить цену" in client.get(f"{SVC}?tab=tariff").text


def test_no_hours_anywhere(client):
    login_as(client)
    client.post(f"{SVC}/tariff", data={"tariff_code": "PLATINUM"})
    for tab in ("data", "tariff"):
        page = client.get(f"{SVC}?tab={tab}").text
        assert "Срок" not in page and 'name="duration_code"' not in page
    assert "Срок" not in client.get("/cabinet").text
    assert "Срок" not in client.get("/cabinet/offer").text
    login_as(client, "operator")
    assert "Сроки" not in client.get("/admin").text
    assert client.get("/admin/durations").status_code == 404
    assert client.post("/admin/data/duration", data={"code": "48H"}).status_code == 404
    assert "durations" not in client.get("/rc/qos_catalog").json()


def test_mock_session_delete(client):
    created = client.post("/mock-gsma/qod/sessions", json={"qos_profile": {"code": "GOLD"}}).json()
    assert "expires_at" not in created
    gone = client.delete(f"/mock-gsma/qod/sessions/{created['session_id']}")
    assert gone.json()["status"] == "TERMINATED"
