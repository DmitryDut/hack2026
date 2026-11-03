"""Schema-driven validation and forms (docs/SPEC.md §5, D3).

Built-in types (tariff, duration, service, signature) keep their table columns; fields added
through the schema editor live in the row's `extra` JSON.
Custom types are stored in the generic Entity table.
"""

import json
import re
from typing import Any

from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError
from sqlmodel import Session

from app.models import Duration, EntityDef, Service, Signature, Tariff
from app.services import config

SCHEMA_DIR = config.CONFIG_DIR / "schemas"
MODELS = {"tariff": Tariff, "duration": Duration, "service": Service, "signature": Signature}
ALLOWED_TYPES = {"string", "integer", "number", "boolean"}
TYPE_ID = re.compile(r"^[a-z][a-z0-9_]{1,30}$")


def default_schemas() -> dict[str, dict]:
    return {
        p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(SCHEMA_DIR.glob("*.json"))
    }


def get_def(db: Session, type_: str) -> EntityDef | None:
    return db.get(EntityDef, type_)


def schema(db: Session, type_: str) -> dict:
    definition = get_def(db, type_)
    return definition.json_schema if definition else {"type": "object", "properties": {}}


def core_fields(type_: str) -> set[str]:
    model = MODELS.get(type_)
    return set(model.model_fields) - {"extra"} if model else set()


def split(type_: str, data: dict) -> tuple[dict, dict]:
    """(columns, extra) for a built-in type."""
    core = core_fields(type_)
    return (
        {k: v for k, v in data.items() if k in core},
        {k: v for k, v in data.items() if k not in core},
    )


def value_of(obj: Any, name: str) -> Any:
    if name in type(obj).model_fields and name != "extra":
        return getattr(obj, name)
    return (getattr(obj, "extra", None) or {}).get(name)


def options(prop: dict) -> list | None:
    if "enum" in prop:
        return prop["enum"]
    if prop.get("x-ref") == "protocol":
        return [p["code"] for p in config.load("protocols")["protocols"]]
    return None


def fields(db: Session, type_: str) -> list[dict]:
    """Form/table description built from the schema, in declaration order."""
    sch = schema(db, type_)
    required = set(sch.get("required", []))
    result = []
    for name, prop in sch.get("properties", {}).items():
        if prop.get("x-hidden"):
            continue
        opts = options(prop)
        kind = "checkbox" if prop.get("type") == "boolean" else "select" if opts else "text"
        result.append(
            {
                "name": name,
                "title": prop.get("title", name),
                "kind": kind,
                "options": opts or [],
                "required": name in required,
                "placeholder": prop.get("x-placeholder", ""),
                "default": prop.get("default"),
                "type": prop.get("type"),
            }
        )
    return result


def coerce(prop: dict, raw: Any) -> Any:
    if prop.get("type") == "boolean":
        return raw in (True, "on", "true", "1", "yes")
    if raw is None:
        return None
    raw = raw.strip() if isinstance(raw, str) else raw
    if raw == "":
        return None
    try:
        if prop.get("type") == "integer":
            return int(raw)
        if prop.get("type") == "number":
            return float(str(raw).replace(",", "."))
    except ValueError:
        return raw  # validation will report the type error
    return raw


def coerce_all(sch: dict, raw: dict) -> dict:
    data = {}
    for name, prop in sch.get("properties", {}).items():
        value = coerce(prop, raw.get(name))
        if value is not None:
            data[name] = value
    return data


def _message(prop: dict, error) -> str:
    if "x-error" in prop:
        return prop["x-error"]
    texts = {
        "required": "Обязательное поле",
        "minLength": "Обязательное поле",
        "type": "Неверный тип значения",
        "enum": "Недопустимое значение",
        "pattern": "Неверный формат",
        "format": "Неверный формат",
        "minimum": f"Значение должно быть не меньше {error.validator_value}",
        "maximum": f"Значение должно быть не больше {error.validator_value}",
    }
    return texts.get(error.validator, error.message)


def validate(sch: dict, data: dict) -> dict[str, str]:
    """Field → message; empty dict means valid."""
    errors: dict[str, str] = {}
    props = sch.get("properties", {})
    for err in Draft7Validator(sch, format_checker=Draft7Validator.FORMAT_CHECKER).iter_errors(
        data
    ):
        if err.validator == "required":
            match = re.match(r"'(.+?)' is a required property", err.message)
            field = match.group(1) if match else "_"
        else:
            field = str(err.path[0]) if err.path else "_"
        errors.setdefault(field, _message(props.get(field, {}), err))
    for name, prop in props.items():
        opts = options(prop) if "enum" not in prop else None
        if opts is not None and name in data and data[name] not in opts:
            errors.setdefault(name, prop.get("x-error", "Недопустимое значение"))
    return errors


def check_schema_edit(new: Any, type_: str, builtin: bool) -> list[str]:
    """Problems with a schema submitted from the editor; empty list means acceptable."""
    if not isinstance(new, dict):
        return ["Схема должна быть JSON-объектом"]
    if new.get("type") != "object":
        return ['Корневой "type" должен быть "object"']
    props = new.get("properties")
    if not isinstance(props, dict) or not props:
        return ['Раздел "properties" должен быть непустым объектом']
    try:
        Draft7Validator.check_schema(new)
    except SchemaError as exc:
        return [f"Схема некорректна: {exc.message}"]
    problems = []
    for name, prop in props.items():
        if not isinstance(prop, dict) or prop.get("type") not in ALLOWED_TYPES:
            problems.append(
                f"Поле «{name}»: поддерживаются типы {', '.join(sorted(ALLOWED_TYPES))}"
            )
    required = new.get("required", [])
    if not isinstance(required, list) or any(r not in props for r in required):
        problems.append('"required" должен содержать только существующие поля')
    if builtin:
        base = default_schemas().get(type_, {}).get("properties", {})
        for name, prop in base.items():
            if name not in props or props[name].get("type") != prop.get("type"):
                problems.append(f"Нельзя удалить базовое поле «{name}» или изменить его тип")
    return problems
