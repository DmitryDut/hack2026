from app.models import Tariff
from app.services import config


def _value(factor: dict, tariff: Tariff) -> float:
    if "const" in factor:
        return factor["const"]
    attr = factor["field"].split(".", 1)[1]  # "qos_profile.<attr>": the tariff is the only source
    if attr in type(tariff).model_fields:
        return getattr(tariff, attr)
    return (tariff.extra or {}).get(attr, 0)


def price(tariff: Tariff | None) -> int | None:
    """Monthly price in RUB: product of the factors from config/pricing.yaml."""
    if tariff is None:
        return None
    result = 1.0
    for factor in config.load("pricing")["factors"]:
        result *= _value(factor, tariff)
    return round(result)


def breakdown(tariff: Tariff) -> list[dict]:
    """Factors with labels and values, for the 'how the price is calculated' block."""
    return [
        {"label": f.get("label", ""), "value": f"{_value(f, tariff):g}"}
        for f in config.load("pricing")["factors"]
    ]
