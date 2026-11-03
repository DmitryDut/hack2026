# T-005: Схемы подключения

**Цель:** справочник схем, выбор схемы партнёром (`PartnerConnection`: requested → configured → active), подтверждение оператором.
**Файлы:** `app/services/connection.py`, `app/api/schemes.py`, `app/web/connection.py`, `app/templates/partner/connection*.html`, тесты.
**Критерии приёмки:** только `approved`-партнёр может запросить подключение; переходы пишут AuditEvent; UI + API.
**Вне скоупа:** подключение услуг абонентам.
**Зависит от:** T-001 (для логики approved — согласовать с T-002)
**Журнал:**
