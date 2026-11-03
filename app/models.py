from datetime import UTC, datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


class Partner(SQLModel, table=True):
    partner_id: str = Field(primary_key=True)
    name: str


class Tariff(SQLModel, table=True):
    code: str = Field(primary_key=True)
    name: str
    bitrate_mbps: int
    priority_level: int
    price_multiplier: float
    sla_percent: float
    status: str = "ACTIVE"
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Duration(SQLModel, table=True):
    code: str = Field(primary_key=True)
    hours: int
    price_multiplier: float
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Service(SQLModel, table=True):
    id: str = Field(primary_key=True)
    partner_id: str = Field(index=True)
    name: str
    description: str = ""
    tariff_code: str | None = None
    duration_code: str | None = None
    price_confirmed: bool = False
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Signature(SQLModel, table=True):
    id: str = Field(primary_key=True)
    service_id: str = Field(index=True)
    ipv4: str
    uri: str
    port: int
    protocol: str
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON))


class ServiceState(SQLModel, table=True):
    service_id: str = Field(primary_key=True)
    status: str = "draft"  # draft | in_testing | passed | failed | applied
    session_id: str | None = None
    applied_at: datetime | None = None
    expires_at: datetime | None = None


class TestStep(SQLModel, table=True):
    __test__ = False
    id: int | None = Field(default=None, primary_key=True)
    service_id: str = Field(index=True)
    signature_id: str
    result: str = "pending"  # pending | success | error
    confirmed: bool = False
    error_code: str | None = None
    error_message: str | None = None


class EventLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    partner_id: str = Field(index=True)
    service_id: str | None = None
    entity_type: str = "service"
    event: str
    details: str = "{}"
    created_at: datetime = Field(default_factory=now)


class NetworkRequest(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    partner_id: str = Field(index=True)
    kind: str
    method: str
    path: str
    request: str = "{}"
    response: str = "{}"
    status_code: int = 200
    created_at: datetime = Field(default_factory=now)


class Subscriber(SQLModel, table=True):
    msisdn: str = Field(primary_key=True)
    tariff: str = ""
    region: str = ""


class Assignment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    msisdn: str = Field(index=True)
    service_id: str = Field(index=True)
    assignment_id: str = ""
    status: str = "REQUESTED"  # REQUESTED | AVAILABLE | UNAVAILABLE
    created_at: datetime = Field(default_factory=now)


class EntityDef(SQLModel, table=True):
    """JSON Schema of an entity type (docs/SPEC.md D3).

    Built-in types are backed by tables, the rest by Entity.
    """

    type: str = Field(primary_key=True)
    title: str
    json_schema: dict = Field(default_factory=dict, sa_column=Column(JSON))
    builtin: bool = False


class Entity(SQLModel, table=True):
    id: str = Field(primary_key=True)
    type: str = Field(index=True)
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)
