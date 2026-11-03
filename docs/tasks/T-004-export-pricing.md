# T-004: Экспорт для PX, цена, варианты предложения

**Цель:** EXP-1…EXP-5, CORE-9, PROC-1…PROC-5.
**Данные:** `v1/test_data/expected_export.json`, `v2/test_data/relations.json`, `expected_export.json`, `v5/test_data/expected_px_offer.json`.
**Файлы:** `config/relations.json`, `config/pricing.yaml`, `config/process.yaml`, `config/px_payload.yaml`, `app/services/export.py`, `app/services/pricing.py`, `app/services/offer.py`, `app/api/export.py`, `app/web/offer.py`, тесты.
**Критерии приёмки:**
- `GET /api/v1/partners/{id}/export` совпадает по структуре с эталоном; только подтверждённые назначения; пустой партнёр → `services: []`.
- Цена по формуле из конфига: Platinum 30 000, Gold 10 000 ₽/мес; смена множителя меняет цену без кода.
- Несколько вариантов предложения: создать, сравнить, выбрать; без подтверждения цены тест недоступен.
- Порядок шагов процесса берётся из `process.yaml`.
**Вне скоупа:** мок PX, песочница.
**Зависит от:** T-002
**Журнал:**
