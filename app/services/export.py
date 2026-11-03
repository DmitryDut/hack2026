"""JSON for PX (docs/px-json-proposal.md); the shape is described in config/px_payload.yaml."""

from datetime import datetime

from sqlmodel import Session, select

from app.models import Partner, Service
from app.services import config, sandbox, schema_core


def _pick(obj, spec) -> dict:
    pairs = spec.items() if isinstance(spec, dict) else ((name, name) for name in spec)
    return {out: schema_core.value_of(obj, src) for out, src in pairs}


def build(db: Session, partner_id: str) -> dict:
    cfg = config.load("px_payload")
    partner = db.get(Partner, partner_id)
    result = {
        "schema_version": cfg["schema_version"],
        **_pick(partner, cfg["partner"]["fields"]),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "services": [],
    }
    services = db.exec(select(Service).where(Service.partner_id == partner_id).order_by(Service.id))
    for service in services:
        if not service.price_confirmed:
            continue  # only services with a confirmed price go to PX
        item = _pick(service, cfg["service"]["fields"])
        for name, lookup in cfg["service"].get("lookups", {}).items():
            model = schema_core.MODELS[lookup["entity"]]
            target = db.get(model, getattr(service, lookup["from"]))
            item[name] = _pick(target, lookup["fields"]) if target else None
        item["signatures"] = [
            _pick(s, cfg["signature"]["fields"]) for s in sandbox.signatures(db, service.id)
        ]
        result["services"].append(item)
    return result
