from app.models import Duration, Tariff
from app.services import config


def _value(factor: dict, tariff: Tariff, duration: Duration) -> float:
    if "const" in factor:
        return factor["const"]
    obj_name, attr = factor["field"].split(".", 1)
    obj = {"qos_profile": tariff, "duration": duration}[obj_name]
    return getattr(obj, attr)


def price(tariff: Tariff | None, duration: Duration | None) -> int | None:
    """Monthly price in RUB: product of the factors from config/pricing.yaml."""
    if tariff is None or duration is None:
        return None
    result = 1.0
    for factor in config.load("pricing")["factors"]:
        result *= _value(factor, tariff, duration)
    return round(result)


def breakdown(tariff: Tariff, duration: Duration) -> list[dict]:
    """Factors with labels and values, for the 'how the price is calculated' block."""
    rows = []
    for factor in config.load("pricing")["factors"]:
        value = _value(factor, tariff, duration)
        rows.append({"label": factor.get("label", ""), "value": f"{value:g}"})
    return rows
