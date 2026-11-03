"""Demo data: tariffs, durations, partners, services, signatures, subscribers."""

from sqlmodel import Session, SQLModel

from app.db import engine
from app.models import (
    Duration,
    EntityDef,
    Partner,
    Service,
    ServiceState,
    Signature,
    Subscriber,
    Tariff,
)
from app.services import schema_core

TARIFFS = [
    ("BRONZE", "Бронза", 10, 1, 1.0, 99.0),
    ("SILVER", "Серебро", 30, 2, 1.5, 99.5),
    ("GOLD", "Золото", 50, 3, 2.0, 99.9),
    ("PLATINUM", "Платина", 100, 4, 3.0, 99.95),
    ("DIAMOND", "Бриллиант", 200, 5, 4.0, 99.99),
]
DURATIONS = [("1H", 1, 0.15), ("6H", 6, 0.6), ("12H", 12, 1.0), ("24H", 24, 1.7), ("72H", 72, 4.0)]
SIGNATURES = [
    ("sig-1", "svc-vcs", "10.10.1.5", "vcs.mts-link.ru", 443, "HTTPS"),
    ("sig-2", "svc-vcs", "10.10.1.6", "media.mts-link.ru", 5004, "RTP"),
    ("sig-3", "svc-vcs", "10.10.1.7", "api.mts-link.ru", 8443, "HTTPS"),
    ("sig-4", "svc-vcs", "10.10.1.8", "media2.mts-link.ru", 5005, "RTP"),
    ("sig-5", "svc-chat", "10.10.3.7", "chat.mts-link.ru", 443, "HTTPS"),
]
SUBSCRIBERS = [
    ("+79161230001", "Smart", "Москва"),
    ("+79161230002", "Smart", "Москва"),
    ("+79161230003", "Ультра", "Москва"),
    ("+79161230004", "Smart", "Санкт-Петербург"),
    ("+79161230005", "Ультра", "Санкт-Петербург"),
    ("+79161230006", "Smart", "Казань"),
    ("+79161230007", "Smart", "Казань"),
    ("+79161230008", "Ультра", "Новосибирск"),
    ("+79161230009", "Smart", "Екатеринбург"),
    ("+79161230010", "Ультра", "Москва"),
    ("+79161230011", "Smart", "Самара"),
    ("+79161230012", "Smart", "Москва"),
]


def main() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        for type_, sch in schema_core.default_schemas().items():
            db.add(
                EntityDef(type=type_, title=sch.get("title", type_), json_schema=sch, builtin=True)
            )
        db.add_all(
            Tariff(
                code=c, name=n, bitrate_mbps=b, priority_level=p, price_multiplier=m, sla_percent=s
            )
            for c, n, b, p, m, s in TARIFFS
        )
        db.add_all(Duration(code=c, hours=h, price_multiplier=m) for c, h, m in DURATIONS)
        db.add_all(
            [
                Partner(partner_id="mts-link-1", name="MTS Link"),
                Partner(partner_id="other-partner", name="Другой партнёр"),
            ]
        )
        db.add_all(
            [
                Service(
                    id="svc-vcs",
                    partner_id="mts-link-1",
                    name="Link ВКС",
                    description="Видеоконференцсвязь MTS Link",
                    tariff_code="PLATINUM",
                    duration_code="12H",
                ),
                Service(
                    id="svc-chat",
                    partner_id="mts-link-1",
                    name="Link Чаты",
                    description="Чаты MTS Link",
                    tariff_code="GOLD",
                    duration_code="24H",
                ),
            ]
        )
        db.add_all([ServiceState(service_id="svc-vcs"), ServiceState(service_id="svc-chat")])
        db.add_all(
            Signature(id=i, service_id=s, ipv4=ip, uri=u, port=p, protocol=pr)
            for i, s, ip, u, p, pr in SIGNATURES
        )
        db.add_all(Subscriber(msisdn=m, tariff=t, region=r) for m, t, r in SUBSCRIBERS)
        db.commit()


if __name__ == "__main__":
    main()
