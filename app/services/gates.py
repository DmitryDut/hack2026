"""Tab availability from config/process.yaml: a tab is open when all its gate predicates hold."""

from sqlmodel import Session, select

from app.models import Service, ServiceState, Signature
from app.services import config


def _status(db: Session, service: Service) -> str:
    state = db.get(ServiceState, service.id)
    return state.status if state else "draft"


PREDICATES = {
    "has_signatures": (
        lambda db, s: (
            db.exec(select(Signature).where(Signature.service_id == s.id)).first() is not None
        ),
        "Сначала добавьте сигнатуры",
    ),
    "tariff_set": (lambda db, s: bool(s.tariff_code and s.duration_code), "Выберите тариф и срок"),
    "price_confirmed": (
        lambda db, s: s.price_confirmed,
        "Сначала подтвердите цену на вкладке «Тариф и стоимость»",
    ),
    "test_passed": (
        lambda db, s: _status(db, s) in ("passed", "applied"),
        "Доступно после успешного тестирования",
    ),
    "priority_on": (
        lambda db, s: _status(db, s) == "applied",
        "Доступно после включения приоритета",
    ),
}


def tabs() -> list[tuple[str, str]]:
    return [(t["id"], t["title"]) for t in config.load("process")["tabs"]]


def gates(tab: str) -> list[str]:
    return list(config.load("process").get("gates", {}).get(tab, []))


def reason(db: Session, service: Service, tab: str) -> str | None:
    """Why the tab is closed, or None when it is open."""
    for name in gates(tab):
        check, message = PREDICATES[name]
        if not check(db, service):
            return message
    return None
