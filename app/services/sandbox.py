"""Sandbox state machine (docs/SPEC.md §8): draft → in_testing → passed|failed → applied."""

import json
from datetime import datetime

from sqlmodel import Session, select

from app.mocks import gsma
from app.models import (
    Duration,
    EventLog,
    NetworkRequest,
    Service,
    ServiceState,
    Signature,
    Tariff,
    TestStep,
)
from app.services import config, gates


class RuleError(Exception):
    """Business-rule violation shown to the user."""


def log(db: Session, service: Service, event: str, **details) -> None:
    db.add(
        EventLog(
            partner_id=service.partner_id,
            service_id=service.id,
            event=event,
            details=json.dumps(details, ensure_ascii=False, default=str),
        )
    )


def net(
    db: Session,
    service: Service,
    kind: str,
    method: str,
    path: str,
    request: dict,
    response: dict,
    status: int = 200,
) -> None:
    db.add(
        NetworkRequest(
            partner_id=service.partner_id,
            kind=kind,
            method=method,
            path=path,
            request=json.dumps(request, ensure_ascii=False, default=str),
            response=json.dumps(response, ensure_ascii=False, default=str),
            status_code=status,
        )
    )


def state_of(db: Session, service: Service) -> ServiceState:
    state = db.get(ServiceState, service.id)
    if state is None:
        state = ServiceState(service_id=service.id)
        db.add(state)
        db.commit()
    return state


def signatures(db: Session, service_id: str) -> list[Signature]:
    return list(
        db.exec(select(Signature).where(Signature.service_id == service_id).order_by(Signature.id))
    )


def steps(db: Session, service_id: str) -> list[TestStep]:
    return list(
        db.exec(select(TestStep).where(TestStep.service_id == service_id).order_by(TestStep.id))
    )


def _clear_steps(db: Session, service_id: str) -> None:
    for step in steps(db, service_id):
        db.delete(step)


# ---- change control -------------------------------------------------------


def guard_change(db: Session, service: Service) -> None:
    """Call before any modification: applied services are locked."""
    if state_of(db, service).status == "applied":
        log(db, service, "change_rejected", reason="applied_locked")
        db.commit()
        raise RuleError("Приоритет включён — изменения запрещены. Сброс выполняет оператор.")


def after_change(
    db: Session,
    service: Service,
    event: str,
    signature_id: str | None = None,
    changes: dict | None = None,
    reset_reason: str = "signature_modified",
) -> None:
    """Call after a modification: an active test run is reset to draft, the change is logged."""
    state = state_of(db, service)
    if state.status in ("in_testing", "passed", "failed"):
        old = state.status
        _clear_steps(db, service.id)
        state.status = "draft"
        log(
            db,
            service,
            "run_reset",
            reason=reset_reason,
            signature_id=signature_id,
            from_status=old,
            to_status="draft",
        )
    log(db, service, event, signature_id=signature_id, changes=changes or {})
    db.commit()


# ---- price and tariff -----------------------------------------------------


def set_tariff(db: Session, service: Service, tariff_code: str, duration_code: str) -> None:
    tariff, duration = db.get(Tariff, tariff_code), db.get(Duration, duration_code)
    if tariff is None or tariff.status != "ACTIVE" or duration is None:
        raise RuleError("Выберите доступный тариф и срок")
    guard_change(db, service)
    changes = {
        "tariff": {"old": service.tariff_code, "new": tariff_code},
        "duration": {"old": service.duration_code, "new": duration_code},
    }
    service.tariff_code, service.duration_code, service.price_confirmed = (
        tariff_code,
        duration_code,
        False,
    )
    db.add(service)
    db.commit()
    after_change(db, service, "tariff_changed", changes=changes, reset_reason="tariff_modified")


def confirm_price(db: Session, service: Service, price: int | None) -> None:
    if price is None:
        raise RuleError("Сначала выберите тариф и срок")
    guard_change(db, service)
    service.price_confirmed = True
    db.add(service)
    log(db, service, "price_confirmed", price_rub_per_month=price)
    db.commit()


# ---- test run -------------------------------------------------------------


def start(db: Session, service: Service) -> None:
    state = state_of(db, service)
    if state.status != "draft":
        raise RuleError("Тестирование можно начать только из черновика")
    closed = gates.reason(db, service, "test")
    if closed:
        raise RuleError(closed)
    sigs = signatures(db, service.id)
    for sig in sigs:
        db.add(TestStep(service_id=service.id, signature_id=sig.id))
    state.status = "in_testing"
    log(
        db,
        service,
        "run_started",
        service_id=service.id,
        steps_created=len(sigs),
        from_status="draft",
        to_status="in_testing",
    )
    db.commit()


def _step(db: Session, service: Service, signature_id: str) -> TestStep:
    step = next((s for s in steps(db, service.id) if s.signature_id == signature_id), None)
    if step is None:
        raise RuleError("Строка теста не найдена")
    return step


def check(db: Session, service: Service, signature_id: str) -> None:
    state = state_of(db, service)
    if state.status != "in_testing":
        raise RuleError("Проверка доступна только во время тестирования")
    step, sig = _step(db, service, signature_id), db.get(Signature, signature_id)
    if step.result == "success":
        raise RuleError("Строка уже проверена")
    request = {
        "signature": {"ipv4": sig.ipv4, "uri": sig.uri, "port": sig.port, "protocol": sig.protocol},
        "qos_profile_code": service.tariff_code,
        "duration_code": service.duration_code,
    }
    response = gsma.validate(request)
    net(db, service, "gsma_validate", "POST", "/mock-gsma/validate", request, response)
    if response["result"] == "error":
        step.result, step.error_code, step.error_message = (
            "error",
            response.get("error_code"),
            response.get("error_message"),
        )
        log(
            db,
            service,
            "step_checked",
            signature_id=signature_id,
            result="error",
            error_code=response.get("error_code"),
        )
        state.status = "failed"
        log(
            db,
            service,
            "run_failed",
            service_id=service.id,
            reason="step_error",
            from_status="in_testing",
            to_status="failed",
        )
    else:
        step.result = "success"
        log(db, service, "step_checked", signature_id=signature_id, result="success")
    db.commit()


def confirm(db: Session, service: Service, signature_id: str) -> None:
    state = state_of(db, service)
    step = _step(db, service, signature_id)
    if state.status != "in_testing" or step.result != "success":
        raise RuleError("Подтвердить можно только успешно проверенную строку")
    step.confirmed = True
    log(db, service, "step_confirmed", signature_id=signature_id, by_user=True)
    if all(s.result == "success" and s.confirmed for s in steps(db, service.id)):
        state.status = "passed"
        log(
            db,
            service,
            "run_passed",
            service_id=service.id,
            from_status="in_testing",
            to_status="passed",
        )
    db.commit()


def back(db: Session, service: Service) -> None:
    state = state_of(db, service)
    if state.status != "failed":
        raise RuleError("Вернуться к настройке можно после неуспешного теста")
    _clear_steps(db, service.id)
    state.status = "draft"
    log(db, service, "run_reset", reason="user_back", from_status="failed", to_status="draft")
    db.commit()


# ---- activation -----------------------------------------------------------


def _payload(
    db: Session, service: Service, tariff: Tariff, duration: Duration, sigs: list[Signature]
) -> dict:
    transport = {p["code"]: p["transport"] for p in config.load("protocols")["protocols"]}
    proto_number = {"tcp": 6, "udp": 17}
    return {
        "partner_id": service.partner_id,
        "service": service.name,
        "qos_profile": {"code": tariff.code, "bitrate_mbps": tariff.bitrate_mbps},
        "duration": {"code": duration.code, "hours": duration.hours},
        "signatures": [
            {"ipv4": s.ipv4, "uri": s.uri, "port": s.port, "protocol": s.protocol} for s in sigs
        ],
        "camara": {
            "qosProfile": tariff.code,
            "duration": duration.hours * 3600,
            "applicationServer": {"ipAddresses": sorted({s.ipv4 for s in sigs})},
            "applicationServerPorts": {"ports": sorted({s.port for s in sigs})},
        },
        "pfd": {
            "flowDescriptions": [
                f"permit out {proto_number[transport[s.protocol]]} from {s.ipv4} {s.port} to any"
                for s in sigs
            ],
            "urls": [],
            "domainNames": sorted({s.uri for s in sigs}),
        },
    }


def preview(db: Session, service: Service) -> dict:
    tariff, duration = db.get(Tariff, service.tariff_code), db.get(Duration, service.duration_code)
    return _payload(db, service, tariff, duration, signatures(db, service.id))


def apply(db: Session, service: Service) -> None:
    state = state_of(db, service)
    if state.status != "passed":
        raise RuleError("Включить приоритет можно после успешного тестирования")
    closed = gates.reason(db, service, "launch")
    if closed:
        raise RuleError(closed)
    if not (service.tariff_code and service.duration_code):
        raise RuleError("Выберите тариф и срок")
    sigs = signatures(db, service.id)
    if len({s.ipv4 for s in sigs}) > 16:
        raise RuleError("Допускается не более 16 уникальных IP-адресов")
    tariff, duration = db.get(Tariff, service.tariff_code), db.get(Duration, service.duration_code)
    payload = _payload(db, service, tariff, duration, sigs)
    response = gsma.create_session(payload)
    started = datetime.fromisoformat(response["started_at"])
    expires = datetime.fromisoformat(response["expires_at"])
    session_id = response["session_id"]
    net(
        db,
        service,
        "gsma_session",
        "POST",
        "/mock-gsma/qod/sessions",
        payload,
        response,
        201,
    )
    state.status, state.session_id, state.applied_at, state.expires_at = (
        "applied",
        session_id,
        started,
        expires,
    )
    log(
        db,
        service,
        "applied_to_production",
        service_id=service.id,
        session_id=session_id,
        from_status="passed",
        to_status="applied",
    )
    db.commit()


def operator_reset(db: Session, service: Service) -> None:
    state = state_of(db, service)
    if state.status != "applied":
        raise RuleError("Сбросить можно только запущенную услугу")
    _clear_steps(db, service.id)
    state.status, state.session_id, state.applied_at, state.expires_at = "draft", None, None, None
    log(db, service, "applied_reset", reason="operator")
    db.commit()
