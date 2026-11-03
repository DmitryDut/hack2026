from datetime import datetime
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def rub(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{round(value):,}".replace(",", " ")


def hm(value: datetime | None) -> str:
    return value.astimezone().strftime("%H:%M") if value else "—"


def dtf(value: datetime | None) -> str:
    return value.astimezone().strftime("%d.%m %H:%M:%S") if value else "—"


def phone(value: str | None) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if len(digits) != 11:
        return value or "—"
    return f"+7 {digits[1:4]} {digits[4:7]} {digits[7:9]} {digits[9:]}"


templates.env.filters["rub"] = rub
templates.env.filters["phone"] = phone
templates.env.filters["hm"] = hm
templates.env.filters["dtf"] = dtf


def flash_from(request: Request) -> dict | None:
    for kind in ("ok", "error", "info"):
        text = request.query_params.get(kind)
        if text:
            return {"kind": kind, "text": text}
    return None


def render(request: Request, name: str, user=None, status_code: int = 200, **ctx):
    ctx.setdefault("flash", flash_from(request))
    ctx.setdefault("embed", request.cookies.get("qod_embed") == "1")
    return templates.TemplateResponse(request, name, {"user": user, **ctx}, status_code=status_code)


EVENT_LABELS = {
    "run_started": "Тестирование начато",
    "step_checked": "Сигнатура проверена",
    "step_confirmed": "Результат подтверждён",
    "run_failed": "Тест не пройден",
    "run_passed": "Тест пройден",
    "run_reset": "Тестирование сброшено",
    "signature_added": "Сигнатура добавлена",
    "signature_updated": "Сигнатура изменена",
    "signature_deleted": "Сигнатура удалена",
    "tariff_changed": "Тариф или срок изменён",
    "price_confirmed": "Цена подтверждена",
    "applied_to_production": "Приоритет включён",
    "applied_reset": "Сброшено оператором",
    "change_rejected": "Изменение отклонено",
    "assignment_requested": "Подключение запрошено",
    "assignment_available": "Подключение доступно",
}
templates.env.filters["event_label"] = lambda code: EVENT_LABELS.get(code, code)
templates.env.filters["pretty"] = lambda raw: __import__("json").dumps(
    __import__("json").loads(raw), ensure_ascii=False, indent=2
)
