"""P4: demo run journal matches V4 `expected_event_log.json`; transitions are guarded."""

import json
from pathlib import Path

from sqlmodel import Session, select

from app.db import engine
from app.models import EventLog
from tests.conftest import login_as

EXPECTED = json.loads((Path(__file__).parent / "fixtures" / "expected_event_log.json").read_text())[
    "events"
]
RUN_EVENTS = {
    "run_started",
    "step_checked",
    "step_confirmed",
    "run_failed",
    "run_reset",
    "run_passed",
    "signature_updated",
    "applied_to_production",
}
SVC = "/cabinet/services/svc-vcs"


def test_event_journal_matches_reference(client):
    login_as(client)
    client.post(f"{SVC}/tariff", data={"tariff_code": "PLATINUM"})
    client.post(f"{SVC}/confirm-price")
    client.post(f"{SVC}/test/start")
    for sig in ("sig-1", "sig-2", "sig-3"):
        client.post(f"{SVC}/test/check/{sig}")
        client.post(f"{SVC}/test/confirm/{sig}")
    client.post(f"{SVC}/test/check/sig-4")
    client.post(f"{SVC}/test/back")
    client.post(
        f"{SVC}/signatures/sig-4",
        data={"ipv4": "10.10.1.8", "uri": "media2.mts-link.ru", "port": "5006", "protocol": "RTP"},
    )
    client.post(f"{SVC}/test/start")
    for sig in ("sig-1", "sig-2", "sig-3", "sig-4"):
        client.post(f"{SVC}/test/check/{sig}")
        client.post(f"{SVC}/test/confirm/{sig}")
    client.post(f"{SVC}/apply")
    with Session(engine) as db:
        events = [
            e.event
            for e in db.exec(select(EventLog).order_by(EventLog.id))
            if e.event in RUN_EVENTS
        ]
    assert events == [e["event"] for e in EXPECTED]


def test_transitions_are_guarded(client):
    login_as(client)
    assert "Сначала подтвердите цену" in client.post(f"{SVC}/test/start").text
    assert "только во время тестирования" in client.post(f"{SVC}/test/check/sig-1").text
    assert "после успешного тестирования" in client.post(f"{SVC}/apply").text
