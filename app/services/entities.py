"""CRUD over schema-described types: built-in tables (tariff, duration) and custom entities."""

import secrets

from sqlmodel import Session, select

from app.models import Duration, Entity, EntityDef, Service, Tariff
from app.services import schema_core
from app.services.sandbox import RuleError

TABLES = {"tariff": (Tariff, "code"), "duration": (Duration, "code")}


def types(db: Session) -> list[EntityDef]:
    """Types editable in the reference-data UI: tariffs, durations and every custom type."""
    defs = db.exec(select(EntityDef).order_by(EntityDef.builtin.desc(), EntityDef.type)).all()
    return [d for d in defs if d.type in TABLES or not d.builtin]


def rows(db: Session, type_: str) -> list[dict]:
    if type_ in TABLES:
        model, pk = TABLES[type_]
        items = db.exec(
            select(model).order_by(getattr(model, "bitrate_mbps" if type_ == "tariff" else "hours"))
        ).all()
        names = [f["name"] for f in schema_core.fields(db, type_)]
        return [
            {"id": getattr(i, pk), **{n: schema_core.value_of(i, n) for n in names}} for i in items
        ]
    items = db.exec(select(Entity).where(Entity.type == type_).order_by(Entity.created_at)).all()
    return [{"id": i.id, **i.data} for i in items]


def validate(db: Session, type_: str, raw: dict) -> tuple[dict, dict]:
    sch = schema_core.schema(db, type_)
    data = schema_core.coerce_all(sch, raw)
    for name, prop in sch.get("properties", {}).items():
        if name not in data and "default" in prop and prop.get("type") != "boolean":
            data[name] = prop["default"]
    return data, schema_core.validate(sch, data)


def create(db: Session, type_: str, data: dict) -> str:
    if type_ in TABLES:
        model, pk = TABLES[type_]
        core, extra = schema_core.split(type_, data)
        if db.get(model, core[pk]):
            raise RuleError(f"Запись с кодом {core[pk]} уже есть")
        db.add(model(**core, extra=extra))
        db.commit()
        return core[pk]
    entity = Entity(id=f"{type_[:3]}-{secrets.token_hex(3)}", type=type_, data=data)
    db.add(entity)
    db.commit()
    return entity.id


def update(db: Session, type_: str, id_: str, data: dict) -> None:
    if type_ in TABLES:
        model, pk = TABLES[type_]
        row = db.get(model, id_)
        if row is None:
            raise RuleError("Запись не найдена")
        core, extra = schema_core.split(type_, data)
        for name, value in core.items():
            if name != pk:
                setattr(row, name, value)
        row.extra = extra
        db.add(row)
    else:
        entity = db.get(Entity, id_)
        if entity is None or entity.type != type_:
            raise RuleError("Запись не найдена")
        entity.data = data
        db.add(entity)
    db.commit()


def delete(db: Session, type_: str, id_: str) -> None:
    if type_ in TABLES:
        model, _ = TABLES[type_]
        column = Service.tariff_code if type_ == "tariff" else Service.duration_code
        if db.exec(select(Service).where(column == id_)).first():
            raise RuleError(
                "Запись используется в услугах — удалить нельзя. Переведите тариф в INACTIVE."
            )
        row = db.get(model, id_)
    else:
        row = db.get(Entity, id_)
    if row is not None:
        db.delete(row)
        db.commit()


def create_type(db: Session, type_: str, title: str) -> None:
    if not schema_core.TYPE_ID.match(type_):
        raise RuleError(
            "Идентификатор типа: строчная латиница, цифры и _ (2–31 символ), начинается с буквы"
        )
    if db.get(EntityDef, type_):
        raise RuleError("Тип с таким идентификатором уже есть")
    sch = {
        "title": title or type_,
        "type": "object",
        "properties": {"name": {"type": "string", "title": "Название", "minLength": 1}},
        "required": ["name"],
    }
    db.add(EntityDef(type=type_, title=title or type_, json_schema=sch, builtin=False))
    db.commit()


def delete_type(db: Session, type_: str) -> None:
    definition = db.get(EntityDef, type_)
    if definition is None or definition.builtin:
        raise RuleError("Встроенный тип удалить нельзя")
    for entity in db.exec(select(Entity).where(Entity.type == type_)):
        db.delete(entity)
    db.delete(definition)
    db.commit()
