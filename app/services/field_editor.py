"""Visual editor of schema fields (passport of traffic, service fields): add, change, delete."""

import copy
import re

from sqlmodel import Session

from app.services import schema_core
from app.services.sandbox import RuleError

NAME = re.compile(r"^[a-z][a-z0-9_]{1,30}$")
FORMATS = {"": "без формата", "ipv4": "IPv4", "ipv6": "IPv6"}
TYPES = {"string": "Текст", "integer": "Целое число", "number": "Число", "boolean": "Да / нет"}


def _number(raw: str, kind: str):
    raw = (raw or "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        return int(raw) if kind == "integer" else float(raw)
    except ValueError as exc:
        raise RuleError(f"Не число: {raw}") from exc


def _prop(spec: dict, base: dict | None = None) -> dict:
    """Schema property from the form; keeps the unrelated keys of an existing property."""
    prop = dict(base or {})
    kind = prop.get("type") or spec.get("type")
    prop["type"] = kind
    prop["title"] = (spec.get("title") or "").strip() or spec.get("name", "")
    placeholder = (spec.get("placeholder") or "").strip()
    prop.pop("x-placeholder", None)
    if placeholder:
        prop["x-placeholder"] = placeholder
    prop.pop("format", None)
    if kind == "string" and spec.get("format") in ("ipv4", "ipv6"):
        prop["format"] = spec["format"]
    for key in ("minimum", "maximum"):
        prop.pop(key, None)
        if kind in ("integer", "number"):
            value = _number(spec.get(key, ""), kind)
            if value is not None:
                prop[key] = value
    prop.pop("enum", None)
    options = [o.strip() for o in re.split(r"[,\n]", spec.get("options") or "") if o.strip()]
    if kind == "string" and options and "x-ref" not in prop:
        prop["enum"] = options
    return prop


def _save(db: Session, type_: str, schema: dict) -> None:
    definition = schema_core.get_def(db, type_)
    if definition is None:
        raise RuleError("Тип не найден")
    problems = schema_core.check_schema_edit(schema, type_, definition.builtin)
    if problems:
        raise RuleError("; ".join(problems))
    definition.json_schema = schema
    db.add(definition)
    db.commit()


def _schema(db: Session, type_: str) -> dict:
    return copy.deepcopy(schema_core.schema(db, type_))


def describe(db: Session, type_: str) -> list[dict]:
    """Rows for the editor: every property with its settings and whether it is protected."""
    sch = schema_core.schema(db, type_)
    required = set(sch.get("required", []))
    core = schema_core.core_fields(type_)
    rows = []
    for name, prop in sch.get("properties", {}).items():
        kind = prop.get("type")
        rows.append(
            {
                "name": name,
                "title": prop.get("title", name),
                "type": kind,
                "type_title": TYPES.get(kind, kind),
                "required": name in required,
                "format": prop.get("format", ""),
                "minimum": prop.get("minimum", ""),
                "maximum": prop.get("maximum", ""),
                "placeholder": prop.get("x-placeholder", ""),
                "options": ", ".join(map(str, prop.get("enum", []))) if "x-ref" not in prop else "",
                "core": name in core,
                "required_locked": name in core and kind in ("integer", "number", "boolean"),
                "deletable": name not in core,
            }
        )
    return rows


def add_field(db: Session, type_: str, spec: dict) -> None:
    name = (spec.get("name") or "").strip()
    if not NAME.match(name):
        raise RuleError("Идентификатор поля: строчная латиница, цифры и _ (2–31 символ)")
    if spec.get("type") not in TYPES:
        raise RuleError("Выберите тип поля")
    schema = _schema(db, type_)
    if name in schema["properties"]:
        raise RuleError("Поле с таким идентификатором уже есть")
    schema["properties"][name] = _prop({**spec, "name": name})
    if spec.get("required"):
        schema.setdefault("required", []).append(name)
    _save(db, type_, schema)


def update_field(db: Session, type_: str, name: str, spec: dict) -> None:
    schema = _schema(db, type_)
    if name not in schema["properties"]:
        raise RuleError("Поле не найдено")
    schema["properties"][name] = _prop({**spec, "name": name}, schema["properties"][name])
    required = [r for r in schema.get("required", []) if r != name]
    locked = name in schema_core.core_fields(type_) and schema["properties"][name]["type"] in (
        "integer",
        "number",
        "boolean",
    )
    if spec.get("required") or (locked and name in schema.get("required", [])):
        required.append(name)
    schema["required"] = required
    _save(db, type_, schema)


def delete_field(db: Session, type_: str, name: str) -> None:
    if name in schema_core.core_fields(type_):
        raise RuleError("Базовое поле удалить нельзя")
    schema = _schema(db, type_)
    if name not in schema["properties"]:
        raise RuleError("Поле не найдено")
    del schema["properties"][name]
    schema["required"] = [r for r in schema.get("required", []) if r != name]
    _save(db, type_, schema)
