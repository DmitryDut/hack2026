# T-002: Справочники, стартовые схемы, сид, валидации

**Цель:** DATA-1…DATA-9, CORE-4.
**Данные:** `v1/test_data/seed.json`, `invalid_signatures.json`; SLA — из `v5/test_data/qos_catalog.json`.
**Файлы:** `scripts/seed.py`, `config/schemas/*.json` (стартовые схемы), `app/services/data_rules.py`, `tests/test_data_rules.py`.
**Критерии приёмки:**
- `make reset`: 9 протоколов, 5 профилей (Bronze…Diamond, SLA), Duration 1H…72H, партнёр `mts-link-1`, «Link ВКС» с сигнатурами и подтверждённым назначением.
- Порт 70000, протокол SMTP — отклонены; дубликат → 409; каскадное удаление сервиса.
- Прогон всех кейсов из `invalid_signatures.json`.
**Вне скоупа:** UI, экспорт.
**Зависит от:** T-001
**Журнал:**
