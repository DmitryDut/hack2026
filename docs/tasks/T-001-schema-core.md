# T-001: Ядро схем и универсальный CRUD

**Цель:** модель, API и валидация из JSON Schema в БД. Требования: CORE-1, CORE-2, CORE-3, CORE-4, CORE-8.
**Данные:** `v2/test_data/entity_schemas.json`, `seed_entities.json`.
**Файлы:** `app/models.py` (`EntityDef`, `Entity`), `app/services/schema_core.py`, `app/api/entities.py`, `pyproject.toml` (+`jsonschema`, `pyyaml`; ADR 0003), `tests/test_schema_core.py`.
**Критерии приёмки:**
- `GET/PUT /api/v1/schemas[/{type}]`; PUT проверяет схему как JSON Schema, кривая → 422, старая цела.
- `POST/GET/PUT/DELETE /api/v1/entity/{type}`; неизвестный тип → 404; нарушение схемы → 422 с указанием поля.
- Записи по старой схеме читаются после смены схемы.
- Тесты на каждый пункт (V2 A1, A7, A8).
**Вне скоупа:** UI, справочники и сид.
**Зависит от:** T-000
**Журнал:**
