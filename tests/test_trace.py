"""P3: storefront flow from the task diagram with the 17-message trace (V5 A6)."""

import json
from pathlib import Path

FLOW = json.loads((Path(__file__).parent / "fixtures" / "flow_trace_template.json").read_text())[
    "flow"
]


def run_flow(client):
    page = client.get("/qos_platform/landing").text
    session = page.split('name="session" value="')[1].split('"')[0]
    client.post(
        "/qos_platform/reg",
        data={
            "session": session,
            "company": "Ромашка",
            "contact": "a@b.ru",
            "traffic": "Видеосвязь",
        },
    )
    return session, client.post(
        "/qos_platform", data={"session": session, "client_id": "partners-1", "profile": "GOLD"}
    )


def test_trace_covers_all_17_messages_in_order(client):
    session, done = run_flow(client)
    assert "Партнёр подключён" in done.text and "покрыто реплик 17 из 17" in done.text
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import TraceEntry

    with Session(engine) as db:
        rows = db.exec(
            select(TraceEntry).where(TraceEntry.session == session).order_by(TraceEntry.id)
        ).all()
    assert [r.seq for r in rows] == list(range(1, 18))
    for row, expected in zip(rows, FLOW, strict=True):
        assert (row.sender, row.receiver) == (expected["from"], expected["to"])
        head = expected["message"].split(" ")[0]
        if head in ("GET", "POST", "200"):  # request/status lines are fixed; content lines vary
            assert row.message.split(" ")[0] == head


def test_flow_registers_partner_and_shows_price(client):
    _, done = run_flow(client)
    assert "partners-1" in done.text and "qos_profiles-1" in done.text and "SLA 99.9" in done.text
    assert "10 000" in done.text
    assert "partners-1" in client.get("/px-showcase?partner=partners-1").text


def test_flow_validation(client):
    assert client.post("/qos_platform/reg", data={"company": "", "contact": ""}).status_code == 422
    session = "abc"
    assert (
        client.post(
            "/qos_platform", data={"session": session, "client_id": "x", "profile": "NOPE"}
        ).status_code
        == 422
    )


def test_showcase_shows_last_trace(client):
    run_flow(client)
    assert "покрыто реплик 17 из 17" in client.get("/px-showcase").text
