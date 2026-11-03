import json
import re
import secrets

from sqlmodel import Session, select

from app.models import Assignment, Service, Subscriber, Tariff
from app.services import sandbox
from app.services.sandbox import RuleError


def normalize(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    return None


def connect(db: Session, service: Service, raw_msisdn: str) -> Assignment:
    if sandbox.state_of(db, service).status != "applied":
        raise RuleError("Сначала включите приоритет для услуги")
    msisdn = normalize(raw_msisdn)
    if msisdn is None:
        raise RuleError("Неверный формат номера: ожидается +7XXXXXXXXXX")
    if db.get(Subscriber, msisdn) is None:
        raise RuleError("Абонент не найден")
    if db.exec(
        select(Assignment).where(Assignment.msisdn == msisdn, Assignment.service_id == service.id)
    ).first():
        raise RuleError("Этот сервис уже подключён абоненту")
    tariff = db.get(Tariff, service.tariff_code)
    assignment_id = f"asg-{secrets.token_hex(2)}"
    request = {"device": {"phoneNumber": msisdn}, "qosProfile": tariff.code}
    sandbox.net(
        db,
        service,
        "qos_assignment_create",
        "POST",
        "/mock-gsma/qos-assignments",
        request,
        {"assignmentId": assignment_id, "status": "REQUESTED"},
        201,
    )
    sandbox.log(db, service, "assignment_requested", msisdn=msisdn, assignment_id=assignment_id)
    sandbox.net(
        db,
        service,
        "qos_assignment_get",
        "GET",
        f"/mock-gsma/qos-assignments/{assignment_id}",
        {},
        {"assignmentId": assignment_id, "status": "AVAILABLE"},
    )
    sandbox.log(db, service, "assignment_available", msisdn=msisdn, assignment_id=assignment_id)
    row = Assignment(
        msisdn=msisdn, service_id=service.id, assignment_id=assignment_id, status="AVAILABLE"
    )
    db.add(row)
    db.commit()
    return row


def details(raw: str) -> dict:
    try:
        return json.loads(raw)
    except ValueError:
        return {}
