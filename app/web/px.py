"""PX storefront mock, embed entry, mock PX and Resource Catalog (docs/SPEC.md §6, §10)."""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.db import get_session
from app.models import Duration, NetworkRequest, Partner, Tariff
from app.services import auth, pricing, schema_core
from app.templating import render

router = APIRouter()


def _log(
    db: Session, partner_id: str, kind: str, method: str, path: str, request, response, status=200
):
    db.add(
        NetworkRequest(
            partner_id=partner_id,
            kind=kind,
            method=method,
            path=path,
            request=json.dumps(request, ensure_ascii=False, default=str),
            response=json.dumps(response, ensure_ascii=False, default=str),
            status_code=status,
        )
    )
    db.commit()


# ---- storefront and embed ---------------------------------------------------


@router.get("/px-showcase")
def showcase(request: Request, partner: str = "mts-link-1", db: Session = Depends(get_session)):
    partners = db.exec(select(Partner).order_by(Partner.name)).all()
    current = db.get(Partner, partner) or partners[0]
    token = auth.partner_token(current.partner_id, current.name)
    return render(
        request,
        "px_showcase.html",
        user=auth.current_user(request),
        partners=partners,
        current=current,
        token=token,
    )


@router.get("/embed")
def embed(request: Request, token: str = "", mode: str = ""):
    payload, reason = auth.explain_token(token)
    if payload is None or payload.get("role") != "partner":
        return render(
            request,
            "embed_error.html",
            status_code=401,
            reason=reason or "токен не даёт доступа к кабинету партнёра",
        )
    response = RedirectResponse("/cabinet", 303)
    response.set_cookie(auth.COOKIE, token, httponly=True, samesite="lax")
    if mode == "tab":
        response.delete_cookie("qod_embed")
    else:
        response.set_cookie("qod_embed", "1", samesite="lax")
    return response


# ---- Resource Catalog and PX mocks ---------------------------------------------


@router.get("/rc/qos_catalog")
def qos_catalog(db: Session = Depends(get_session)):
    tariffs = db.exec(
        select(Tariff).where(Tariff.status == "ACTIVE").order_by(Tariff.bitrate_mbps)
    ).all()
    body = {
        "profiles": [
            {
                "code": t.code,
                "name": t.name,
                "bitrate_mbps": t.bitrate_mbps,
                "sla_percent": t.sla_percent,
                "price_multiplier": t.price_multiplier,
            }
            for t in tariffs
        ],
        "durations": [
            {"code": d.code, "hours": d.hours}
            for d in db.exec(select(Duration).order_by(Duration.hours))
        ],
        "protocols": schema_core.options({"x-ref": "protocol"}),
    }
    _log(db, "-", "rc_catalog", "GET", "/rc/qos_catalog", {}, {"profiles": len(body["profiles"])})
    return body


@router.post("/px/reg")
async def px_reg(request: Request, db: Session = Depends(get_session)):
    data = await request.json()
    numbers = [
        int(p.partner_id.split("-")[-1])
        for p in db.exec(select(Partner))
        if p.partner_id.startswith("partners-") and p.partner_id.split("-")[-1].isdigit()
    ]
    partner_id = f"partners-{max(numbers, default=0) + 1}"
    db.add(Partner(partner_id=partner_id, name=str(data.get("company") or partner_id)))
    db.commit()
    _log(db, partner_id, "px_reg", "POST", "/px/reg", data, {"id": partner_id})
    return {"id": partner_id}


@router.post("/px/save_qos")
async def px_save_qos(request: Request, db: Session = Depends(get_session)):
    data = await request.json()
    count = (
        len(db.exec(select(NetworkRequest).where(NetworkRequest.kind == "px_save_qos")).all()) + 1
    )
    body = {"id": f"qos_profiles-{count}"}
    _log(db, str(data.get("client_id", "-")), "px_save_qos", "POST", "/px/save_qos", data, body)
    return body


@router.post("/px/price")
async def px_price(request: Request, db: Session = Depends(get_session)):
    """PX prices the exported configuration (the mock uses the platform formula)."""
    data = await request.json()
    items, total = [], 0
    for service in data.get("services", []):
        tariff = db.get(Tariff, (service.get("qos_profile") or {}).get("code"))
        duration = db.get(Duration, (service.get("duration") or {}).get("code"))
        price = pricing.price(tariff, duration) or 0
        items.append({"service_id": service.get("service_id"), "price_rub_per_month": price})
        total += price
    body = {
        "offer_id": f"offer-{data.get('partner_id', '')}",
        "currency": "RUB",
        "items": items,
        "total_price_rub_per_month": total,
    }
    _log(
        db,
        str(data.get("partner_id", "-")),
        "px_price",
        "POST",
        "/px/price",
        {"services": len(data.get("services", []))},
        body,
    )
    return body
