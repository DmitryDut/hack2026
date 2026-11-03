# Архитектура

Один процесс FastAPI: HTML (Jinja2 + HTMX), JSON API, SQLite. Модель данных и формы — по JSON Schema из БД (ADR 0003).

```text
Витрина PX (мок, страница)  ──iframe + token──►  Конфигуратор (HTML, HTMX)
        ▲  postMessage(qod:export)                    │
        │                                             ▼
        │                         app/api  ──►  app/services  ──►  SQLite
        │                         /api/v1/entity/{type}        entity_defs (схемы)
        │                         /api/v1/schemas/{type}       entities (данные)
        │                         /api/v1/partners/{id}/export  TestRun/TestStep/EventLog
        │                                             │         NetworkRequest, TraceEntry
        │                                             ▼
        └──── карточка предложения           app/mocks: px, resource_catalog, gsma_qod
                                              (/px/*, /rc/*, /mock-gsma/*) → NetworkRequest
```

## Компоненты
- **Ядро схем** (`app/services/schema_core.py`): CRUD по типам, валидация `jsonschema`, проверка самих схем, экспорт по конфигу связей. Типы сущностей кодом не перечисляются.
- **Рендерер форм** (`app/services/form_render.py` + шаблоны): JSON Schema → поля формы и колонки таблицы. Поддерживаем string / integer / number / boolean / enum, required, pattern, minimum/maximum, format.
- **Админка схем**: редактор JSON Schema, PUT с проверкой, обновление UI без рестарта.
- **Процесс и цена** (`config/process.yaml`, `config/pricing.yaml`): шаги и формула цены — данные, не код.
- **Автомат песочницы** (`app/services/sandbox.py`): Draft/InTesting/Passed/Failed/Applied, сброс при правках, запись `EventLog`.
- **Моки** (`app/mocks/`): PX (`/px/reg`, `/px/save_qos`), каталог (`/rc/qos_catalog`), GSMA APIgw (`/mock-gsma/validate`, `/mock-gsma/qod/sessions`), QoS Provisioning для абонента. Поведение — по данным сценария (детерминированно), задержка 300–800 мс. Каждый вызов пишется в `NetworkRequest`.
- **Встраивание**: HMAC-токен (`PX_SECRET`), `?embed=1`, `postMessage`, CSP `frame-ancestors`, фолбэк «в новой вкладке». Трассировка 17 реплик — `TraceEntry`.

## Стек
FastAPI, SQLModel/SQLAlchemy + SQLite, Jinja2 + HTMX + Pico.css, `jsonschema`, `pyyaml`; `uv`, `ruff`, `pytest` (ADR 0001, 0003).

## Параллельная работа агентов
Фичи разнесены по файлам; общие `models.py`, `main.py`, `seed.py`, `config/` меняются только по карточке задачи.

Решения — в `docs/decisions/`.
