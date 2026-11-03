"""Offer variants: snapshots of tariff/term choices that can be compared and applied."""

from sqlmodel import Session, select

from app.models import Duration, Offer, Service, Tariff
from app.services import pricing, sandbox
from app.services.sandbox import RuleError


def _priced(db: Session, tariff_code: str | None, duration_code: str | None) -> dict:
    tariff = db.get(Tariff, tariff_code) if tariff_code else None
    duration = db.get(Duration, duration_code) if duration_code else None
    return {
        "tariff": tariff.name if tariff else None,
        "hours": duration.hours if duration else None,
        "price": pricing.price(tariff, duration),
    }


def services_of(db: Session, partner_id: str) -> list[Service]:
    return list(
        db.exec(select(Service).where(Service.partner_id == partner_id).order_by(Service.name))
    )


def current(db: Session, partner_id: str) -> list[dict]:
    return [
        {
            "service_id": s.id,
            "name": s.name,
            "tariff_code": s.tariff_code,
            "duration_code": s.duration_code,
            "confirmed": s.price_confirmed,
            **_priced(db, s.tariff_code, s.duration_code),
        }
        for s in services_of(db, partner_id)
    ]


def save_variant(db: Session, partner_id: str, name: str) -> Offer:
    if not name.strip():
        raise RuleError("Укажите название варианта")
    items = [
        {
            "service_id": i["service_id"],
            "tariff_code": i["tariff_code"],
            "duration_code": i["duration_code"],
        }
        for i in current(db, partner_id)
        if i["tariff_code"] and i["duration_code"]
    ]
    if not items:
        raise RuleError("Сначала выберите тариф и срок хотя бы для одной услуги")
    offer = Offer(partner_id=partner_id, name=name.strip(), items=items)
    db.add(offer)
    db.commit()
    return offer


def variants(db: Session, partner_id: str) -> list[Offer]:
    return list(db.exec(select(Offer).where(Offer.partner_id == partner_id).order_by(Offer.id)))


def table(db: Session, partner_id: str) -> dict:
    """Comparison table: one row per service, a column for the current state and each variant."""
    cols = [{"title": "Текущий выбор", "id": None, "cells": {}, "total": 0}]
    for item in current(db, partner_id):
        cols[0]["cells"][item["service_id"]] = item
        cols[0]["total"] += item["price"] or 0
    for offer in variants(db, partner_id):
        col = {"title": offer.name, "id": offer.id, "cells": {}, "total": 0}
        for it in offer.items:
            priced = _priced(db, it["tariff_code"], it["duration_code"])
            col["cells"][it["service_id"]] = priced
            col["total"] += priced["price"] or 0
        cols.append(col)
    return {"services": [(s.id, s.name) for s in services_of(db, partner_id)], "cols": cols}


def apply(db: Session, partner_id: str, offer: Offer) -> tuple[int, int]:
    """Copy the variant's tariffs onto the services; returns (applied, skipped)."""
    done = skipped = 0
    for it in offer.items:
        service = db.get(Service, it["service_id"])
        if service is None or service.partner_id != partner_id:
            skipped += 1
            continue
        try:
            sandbox.set_tariff(db, service, it["tariff_code"], it["duration_code"])
            done += 1
        except RuleError:
            skipped += 1
    return done, skipped
