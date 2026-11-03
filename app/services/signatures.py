from sqlmodel import Session, select

from app.models import Service, Signature
from app.services import sandbox, schema_core


def protocols() -> list[str]:
    from app.services import config

    return [p["code"] for p in config.load("protocols")["protocols"]]


def validate(
    db: Session, service_id: str, raw: dict, exclude_id: str | None = None
) -> tuple[dict, dict]:
    """(typed data, field errors): rules from the 'signature' schema, duplicates checked here."""
    sch = schema_core.schema(db, "signature")
    data = schema_core.coerce_all(sch, raw)
    errors = schema_core.validate(sch, data)
    if not errors:
        key = tuple(data.get(k) for k in ("ipv4", "uri", "port", "protocol"))
        for other in db.exec(select(Signature).where(Signature.service_id == service_id)):
            if (
                other.ipv4,
                other.uri,
                other.port,
                other.protocol,
            ) == key and other.id != exclude_id:
                errors["_"] = "Такая сигнатура уже есть у услуги"
    return data, errors


def _next_id(db: Session) -> str:
    numbers = [
        int(s.id.split("-")[1]) for s in db.exec(select(Signature)) if s.id.split("-")[-1].isdigit()
    ]
    return f"sig-{max(numbers, default=0) + 1}"


def add(db: Session, service: Service, data: dict) -> Signature:
    sandbox.guard_change(db, service)
    core, extra = schema_core.split("signature", data)
    sig = Signature(
        id=_next_id(db),
        service_id=service.id,
        ipv4=core.get("ipv4", ""),
        uri=core.get("uri", ""),
        port=core.get("port", 0),
        protocol=core.get("protocol", ""),
        extra=extra,
    )
    db.add(sig)
    db.commit()
    sandbox.after_change(db, service, "signature_added", signature_id=sig.id)
    return sig


def update(db: Session, service: Service, sig: Signature, data: dict) -> None:
    sandbox.guard_change(db, service)
    core, extra = schema_core.split("signature", data)
    changes = {}
    for name in schema_core.schema(db, "signature").get("properties", {}):
        new = data.get(name)
        old = schema_core.value_of(sig, name)
        if new != old and not (new is None and old in ("", None)):
            changes[name] = {"old": old, "new": new}
    for name in ("ipv4", "uri", "port", "protocol"):
        if name in core or name == "uri":
            setattr(sig, name, core.get(name, "" if name == "uri" else getattr(sig, name)))
    sig.extra = extra
    db.add(sig)
    db.commit()
    sandbox.after_change(
        db,
        service,
        "signature_updated",
        signature_id=sig.id,
        changes=changes,
        reset_reason="signature_modified",
    )


def delete(db: Session, service: Service, sig: Signature) -> None:
    sandbox.guard_change(db, service)
    db.delete(sig)
    db.commit()
    sandbox.after_change(
        db, service, "signature_deleted", signature_id=sig.id, reset_reason="signature_modified"
    )
