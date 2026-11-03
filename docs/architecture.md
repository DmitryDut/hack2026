# Архитектура

Один процесс FastAPI: JSON API (`/api/v1/...`) + серверные HTML-страницы (Jinja2 + HTMX) + SQLite.

```
Браузер ──► app/web (HTML) ─┐
Партнёр API ► app/api (JSON) ┴─► app/services ─► app/models ─► SQLite (data/app.db)
                                      └─► AuditEvent (журнал всех переходов)
```

- `app/services/onboarding.py` — заявка партнёра, проверка, одобрение, выдача API-ключа.
- `app/services/connection.py` — схемы подключения и подключение партнёра.
- `app/services/provisioning.py` — подключение услуги абоненту (без реальной сети).
- Роли: переключатель партнёр/оператор в шапке, без авторизации. API партнёра — заголовок `X-API-Key`.
- Параллельная работа агентов: фичи разнесены по отдельным файлам; общие `models.py`, `main.py`,
  `seed.py` меняются только по карточке задачи.

Решения — в `docs/decisions/`.
