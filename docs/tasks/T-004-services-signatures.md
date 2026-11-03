# T-004: Сервисы и сигнатуры

**Цель:** FR-2, FR-3 — партнёр создаёт сервисы и сигнатуры `{IPv4, URI, port, protocol}`.
**Файлы:** `app/services/partner_services.py`, `app/api/services.py`, `app/web/services.py`, `app/templates/partner/services*.html`, тесты.
**Критерии приёмки:**
- CRUD сервисов и сигнатур в UI и API, привязка к `Partner_ID`.
- Валидация: IPv4 или URI, порт 1–65535, protocol из `config/protocols.yaml`.
- Первое добавление переводит партнёра `registered → configuring` через движок.
**Вне скоупа:** профили и Duration.
**Зависит от:** T-002
**Журнал:**
