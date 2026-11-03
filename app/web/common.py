from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.models import Assignment, Duration, Service, Tariff
from app.services import pricing, sandbox
from app.services.priority import priority_view

STATUS = {
    "draft": ("Черновик", ""),
    "in_testing": ("Тест идёт", "badge-info"),
    "failed": ("Тест не пройден", "badge-error"),
    "passed": ("Тест пройден", "badge-info"),
}


def redirect(url: str, ok: str | None = None, error: str | None = None) -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    if ok:
        url += f"{sep}ok={quote(ok)}"
    elif error:
        url += f"{sep}error={quote(error)}"
    return RedirectResponse(url, 303)


def own_service(db: Session, user: dict, service_id: str) -> Service:
    service = db.get(Service, service_id)
    if service is None or service.partner_id != user["partner_id"]:
        raise HTTPException(404, "Услуга не найдена")
    return service


def view(db: Session, service: Service) -> dict:
    tariff = db.get(Tariff, service.tariff_code) if service.tariff_code else None
    duration = db.get(Duration, service.duration_code) if service.duration_code else None
    state = sandbox.state_of(db, service)
    priority = priority_view(state)
    if priority["state"] == "on":
        label, css = "Приоритет активен", "badge-success"
    elif priority["state"] == "expired":
        label, css = "Срок приоритета истёк", "badge-warning"
    else:
        label, css = STATUS[state.status]
    assignments = db.exec(select(Assignment).where(Assignment.service_id == service.id)).all()
    return {
        "service": service,
        "tariff": tariff,
        "duration": duration,
        "state": state,
        "priority": priority,
        "price": pricing.price(tariff, duration),
        "label": label,
        "css": css,
        "sig_count": len(sandbox.signatures(db, service.id)),
        "assignments": assignments,
    }
