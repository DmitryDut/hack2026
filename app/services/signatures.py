import ipaddress

from sqlmodel import Session, select

from app.models import Service, Signature
from app.services import config, sandbox


def protocols() -> list[str]:
    return [p["code"] for p in config.load("protocols")["protocols"]]


def validate(
    db: Session, service_id: str, data: dict, exclude_id: str | None = None
) -> dict[str, str]:
    """Field-level errors for a signature; empty dict = valid."""
    errors: dict[str, str] = {}
    try:
        ipaddress.IPv4Address(data["ipv4"].strip())
    except (ValueError, KeyError):
        errors["ipv4"] = "Неверный адрес IPv4"
    if not data.get("uri", "").strip():
        errors["uri"] = "Укажите URI"
    try:
        port = int(data["port"])
        if not 1 <= port <= 65535:
            raise ValueError
    except (ValueError, KeyError, TypeError):
        errors["port"] = "Порт должен быть от 1 до 65535"
    if data.get("protocol") not in protocols():
        errors["protocol"] = "Недопустимый протокол"
    if not errors:
        for other in db.exec(select(Signature).where(Signature.service_id == service_id)):
            same = (other.ipv4, other.uri, other.port, other.protocol) == (
                data["ipv4"].strip(),
                data["uri"].strip(),
                int(data["port"]),
                data["protocol"],
            )
            if same and other.id != exclude_id:
                errors["_"] = "Такая сигнатура уже есть у услуги"
    return errors


def _next_id(db: Session) -> str:
    numbers = [
        int(s.id.split("-")[1]) for s in db.exec(select(Signature)) if s.id.split("-")[-1].isdigit()
    ]
    return f"sig-{max(numbers, default=0) + 1}"


def add(db: Session, service: Service, data: dict) -> Signature:
    sandbox.guard_change(db, service)
    sig = Signature(
        id=_next_id(db),
        service_id=service.id,
        ipv4=data["ipv4"].strip(),
        uri=data["uri"].strip(),
        port=int(data["port"]),
        protocol=data["protocol"],
    )
    db.add(sig)
    db.commit()
    sandbox.after_change(db, service, "signature_added", signature_id=sig.id)
    return sig


def update(db: Session, service: Service, sig: Signature, data: dict) -> None:
    sandbox.guard_change(db, service)
    changes = {}
    for field, value in (
        ("ipv4", data["ipv4"].strip()),
        ("uri", data["uri"].strip()),
        ("port", int(data["port"])),
        ("protocol", data["protocol"]),
    ):
        if getattr(sig, field) != value:
            changes[field] = {"old": getattr(sig, field), "new": value}
            setattr(sig, field, value)
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
