from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.db import get_session
from app.models import Assignment, EventLog, Service, Subscriber
from app.services import auth, subscribers
from app.templating import render
from app.web.common import view

router = APIRouter()


@router.get("/subscribers/{msisdn}")
def card(request: Request, msisdn: str, db: Session = Depends(get_session)):
    user = auth.current_user(request)
    if not user:
        raise auth.NeedLogin("/login?info=Сессия истекла, войдите снова")
    number = subscribers.normalize(msisdn) or msisdn
    sub = db.get(Subscriber, number)
    if sub is None:
        raise HTTPException(404, "Абонент не найден")
    rows = []
    for assignment in db.exec(select(Assignment).where(Assignment.msisdn == number)):
        service = db.get(Service, assignment.service_id)
        if user["role"] == "partner" and service.partner_id != user["partner_id"]:
            continue
        rows.append({"a": assignment, "v": view(db, service)})
    events = []
    for event in db.exec(
        select(EventLog)
        .where(EventLog.event.in_(["assignment_requested", "assignment_available"]))
        .order_by(EventLog.id)
    ):
        details = subscribers.details(event.details)
        if details.get("msisdn") == number and any(
            r["v"]["service"].id == event.service_id for r in rows
        ):
            events.append((event, details))
    prioritized = [
        r for r in rows if r["a"].status == "AVAILABLE" and r["v"]["priority"]["state"] == "on"
    ]
    return render(
        request,
        "subscriber.html",
        user=user,
        nav="cabinet" if user["role"] == "partner" else "operator",
        sub=sub,
        rows=rows,
        events=events,
        prioritized=prioritized,
    )
