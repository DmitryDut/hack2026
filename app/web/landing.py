"""Storefront flow from the task diagram: landing → registration → profile choice → connected."""

from fastapi import APIRouter, Depends, Form, Request
from sqlmodel import Session

from app.db import get_session
from app.models import Duration, Tariff
from app.services import auth, pricing, trace
from app.templating import render
from app.web import px

router = APIRouter()


def _page(request, db, name, session, **ctx):
    rows = trace.entries(db, session)
    return render(
        request,
        name,
        user=auth.current_user(request),
        session=session,
        trace=rows,
        covered=trace.coverage(rows),
        **ctx,
    )


@router.get("/qos_platform/landing")
def landing(request: Request, db: Session = Depends(get_session)):
    session = trace.new_session()
    trace.log(db, session, 1)
    trace.log(db, session, 2)
    trace.log(db, session, 3)
    trace.log(db, session, 4)
    return _page(request, db, "landing.html", session)


@router.post("/qos_platform/reg")
def register(
    request: Request,
    session: str = Form(""),
    company: str = Form(""),
    contact: str = Form(""),
    traffic: str = Form(""),
    db: Session = Depends(get_session),
):
    if not session or not company.strip() or not contact.strip():
        return _page(
            request,
            db,
            "landing.html",
            session or trace.new_session(),
            status_code=422,
            error="Укажите компанию и контакт",
            form={"company": company, "contact": contact, "traffic": traffic},
        )
    trace.log(db, session, 5)
    trace.log(db, session, 6)
    trace.log(db, session, 7)
    client_id = px.register(
        db, {"company": company.strip(), "contact": contact.strip(), "traffic": traffic}
    )
    trace.log(db, session, 8, client_id=client_id)
    trace.log(db, session, 9)
    catalog = px.catalog(db)
    trace.log(db, session, 10, profiles=", ".join(p["name"] for p in catalog["profiles"]))
    trace.log(db, session, 11)
    trace.log(db, session, 12)
    return _page(
        request,
        db,
        "landing_profile.html",
        session,
        client_id=client_id,
        company=company.strip(),
        profiles=catalog["profiles"],
    )


@router.post("/qos_platform")
def choose(
    request: Request,
    session: str = Form(""),
    client_id: str = Form(""),
    profile: str = Form(""),
    db: Session = Depends(get_session),
):
    tariff = db.get(Tariff, profile)
    if not session or not client_id or tariff is None:
        return _page(
            request,
            db,
            "landing.html",
            session or trace.new_session(),
            status_code=422,
            error="Выберите тариф из списка",
        )
    trace.log(db, session, 13, client_id=client_id, profile=tariff.name)
    trace.log(db, session, 14)
    saved = px.save_qos(db, {"client_id": client_id, "profile": tariff.code})
    trace.log(db, session, 15)
    trace.log(db, session, 16, qos_id=saved["id"])
    trace.log(db, session, 17, client_id=client_id, profile=tariff.name, sla=tariff.sla_percent)
    price = pricing.price(tariff, db.get(Duration, "12H"))
    return _page(
        request,
        db,
        "landing_done.html",
        session,
        client_id=client_id,
        tariff=tariff,
        price=price,
        qos_id=saved["id"],
    )
