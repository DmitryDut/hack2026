from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.db import get_session
from app.models import Partner, Service
from app.services import auth, sandbox
from app.services.sandbox import RuleError
from app.templating import render
from app.web.cabinet import _journal
from app.web.common import redirect, view

router = APIRouter(prefix="/operator")


@router.get("")
def partners(
    request: Request, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    rows = []
    for partner in db.exec(select(Partner)).all():
        services = [
            view(db, s)
            for s in db.exec(select(Service).where(Service.partner_id == partner.partner_id))
        ]
        rows.append(
            {
                "partner": partner,
                "items": services,
                "on": sum(1 for i in services if i["priority"]["state"] == "on"),
            }
        )
    return render(request, "operator.html", user=user, nav="operator", rows=rows)


@router.get("/journal")
def journal(
    request: Request, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    return _journal(request, db, user, request.query_params.get("partner"), "/operator/journal")


@router.post("/services/{service_id}/reset")
def reset(service_id: str, user=Depends(auth.require_operator), db: Session = Depends(get_session)):
    service = db.get(Service, service_id)
    if service is None:
        return redirect("/operator", error="Услуга не найдена")
    try:
        sandbox.operator_reset(db, service)
    except RuleError as exc:
        return redirect("/operator", error=str(exc))
    return redirect("/operator", ok=f"Услуга «{service.name}» сброшена в черновик")
