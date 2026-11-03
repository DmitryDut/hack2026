# T-003: Рендерер форм по схеме и админка схем

**Цель:** CORE-5, CORE-6, CORE-7 — UI строится по схеме; админка меняет модель на лету.
**Данные:** `v2/test_data/demo_change.json`.
**Файлы:** `app/services/form_render.py`, `app/web/entities.py`, `app/web/admin_schemas.py`, `app/templates/entity/*`, `app/templates/admin/*`, тесты.
**Критерии приёмки:**
- Раздел на тип: таблица по полям схемы + форма создания/правки (типы string/integer/number/boolean/enum, required, pattern, min/max).
- Ошибки валидации в форме совпадают с серверными.
- `/admin/schemas`: выбор типа, редактор, сохранение; новый тип создаётся из админки и сразу получает раздел и CRUD; обновление страницы без рестарта (V2 A2, A4, A5).
**Вне скоупа:** React/rjsf.
**Зависит от:** T-001
**Журнал:**
