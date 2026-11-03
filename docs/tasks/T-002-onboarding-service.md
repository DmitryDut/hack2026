# T-002: Сервис онбординга (state machine) + тесты

**Цель:** `app/services/onboarding.py` — создание партнёра, submit, take_in_review, approve (выдаёт api_key), reject.
**Файлы:** `app/services/onboarding.py`, `app/services/audit.py` (запись AuditEvent), `tests/test_onboarding.py`, JSON-роуты `app/api/partners.py`.
**Критерии приёмки:**
- Недопустимые переходы → исключение; каждый переход пишет AuditEvent.
- API: `POST /api/v1/partners`, `POST /api/v1/partners/{id}/submit`, операторские `approve/reject`.
- Тесты на все переходы.
**Вне скоупа:** HTML-страницы.
**Зависит от:** T-001
**Журнал:**
