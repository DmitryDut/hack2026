"""Trace of the 17-message flow from the task diagram (V5 `flow_trace_template.json`)."""

import secrets

from sqlmodel import Session, select

from app.models import TraceEntry

SP, PL, CJ, RC, PX = (
    "Service Provider",
    "Partner Landing",
    "Customer Journey",
    "Resource Catalog",
    "Partner eXperience",
)

# seq: (from, to, message template) — the flow of the diagram, in order
FLOW = {
    1: (SP, PL, "GET /qos_platform/landing"),
    2: (PL, CJ, "GET /cj/qos_platform (empty)"),
    3: (CJ, PL, "content: HTML landing (form company / contact / traffic)"),
    4: (PL, SP, "200 text/html"),
    5: (SP, PL, "POST /qos_platform/reg (form: company, contact, traffic)"),
    6: (PL, CJ, "POST /cj/qos_platform (user = «отправил форму»)"),
    7: (CJ, PX, "POST /px/reg (partners, {company, contact, traffic})"),
    8: (PX, CJ, '200 {"id": "{client_id}"}'),
    9: (CJ, RC, "GET /rc/qos_catalog"),
    10: (RC, CJ, "{profiles}"),
    11: (CJ, PL, "content: HTML «выбор QoS-профиля»"),
    12: (PL, SP, "200 text/html"),
    13: (SP, PL, "POST /qos_platform (form: client_id={client_id}, profile={profile})"),
    14: (PL, CJ, "POST /cj/qos_platform (user = «отправил форму»)"),
    15: (CJ, PX, "POST /px/save_qos (qos_profiles, {client_id, profile})"),
    16: (PX, CJ, '{"id": "{qos_id}"}'),
    17: (CJ, PL, "content: HTML «Партнёр подключён» ({client_id}, {profile}, SLA {sla}%)"),
}


def new_session() -> str:
    return secrets.token_hex(4)


def log(db: Session, session: str, seq: int, **values) -> None:
    sender, receiver, template = FLOW[seq]
    message = template
    for key, value in values.items():
        message = message.replace("{" + key + "}", str(value))
    db.add(TraceEntry(session=session, seq=seq, sender=sender, receiver=receiver, message=message))
    db.commit()


def entries(db: Session, session: str | None) -> list[TraceEntry]:
    if not session:
        return []
    return list(
        db.exec(select(TraceEntry).where(TraceEntry.session == session).order_by(TraceEntry.id))
    )


def last_session(db: Session) -> str | None:
    last = db.exec(select(TraceEntry).order_by(TraceEntry.id.desc())).first()
    return last.session if last else None


def coverage(rows: list[TraceEntry]) -> tuple[int, int]:
    return len({r.seq for r in rows}), len(FLOW)
