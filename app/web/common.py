import json
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.models import Service, Tariff
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
    state = sandbox.state_of(db, service)
    priority = priority_view(state)
    if priority["state"] == "on":
        label, css = "Приоритет активен", "badge-success"
    else:
        label, css = STATUS[state.status]
    return {
        "service": service,
        "tariff": tariff,
        "state": state,
        "priority": priority,
        "price": pricing.price(tariff),
        "label": label,
        "css": css,
        "sig_count": len(sandbox.signatures(db, service.id)),
    }


def parse_details(raw: str) -> dict:
    try:
        return json.loads(raw)
    except ValueError:
        return {}
