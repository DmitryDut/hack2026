# T-006: Подключение услуги абоненту

**Цель:** `app/services/provisioning.py` + `POST /api/v1/subscribers/{msisdn}/services` (заголовок `X-API-Key`) и форма в UI партнёра.
**Критерии приёмки:** услугу можно подключить только при `active` PartnerConnection; статус `pending → active`; AuditEvent; 401/403/404 корректны; тесты.
**Вне скоупа:** эмуляция сети (ADR 0002), карточка абонента.
**Зависит от:** T-002, T-005
**Журнал:**
