# Архитектура

Один процесс FastAPI: HTML-страницы (Jinja2 + HTMX), JSON API, SQLite, YAML-конфиги.

```
iframe в PX ─► app/web (HTML, ?embed=1) ─┐
Внешние API ─► app/api (JSON) ───────────┴─► app/services ─► app/models ─► SQLite
                                                  │
                         config/*.yaml ◄──────────┤  справочники, процесс, шаблон JSON для PX
                                                  ▼
                      app/mocks: px, resource_catalog, gsma_qod_apigw  ──► NetworkRequest (журнал)
```

- `app/services/process.py` — движок процесса: переходы и условия берёт из `config/process.yaml`, пишет `AuditEvent`.
- `app/services/` — `catalog.py` (справочники), `services.py` (сервисы и сигнатуры), `offer.py`, `sandbox.py`, `activation.py`, `subscribers.py`.
- `app/mocks/` — встроенные имитации внешних систем с теми же путями, что в flow задания (`/px/reg`, `/px/save_qos`, `/rc/qos_catalog`) и GSMA QoD APIgw. Каждый вызов пишется в `NetworkRequest`.
- `app/config_loader.py` — читает YAML при старте (перезапуск = применение правок).
- Режим встраивания: `?embed=1` скрывает шапку; `Partner_ID` передаётся параметром (упрощённая сквозная авторизация).
- Параллельная работа агентов: фичи разнесены по файлам; общие `models.py`, `main.py`, `seed.py`, `config/` меняются только по карточке.

Решения — в `docs/decisions/`.
