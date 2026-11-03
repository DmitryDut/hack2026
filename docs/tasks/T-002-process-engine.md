# T-002: Движок процесса + AuditEvent

**Цель:** `app/services/process.py` — переходы статуса партнёра по `config/process.yaml`; единственная точка смены статуса.
**Файлы:** `app/services/process.py`, `app/services/audit.py`, `tests/test_process.py`.
**Критерии приёмки:**
- `transition(partner, action)` проверяет допустимость по конфигу, пишет `AuditEvent`, иначе исключение.
- Возврат `sandbox → configuring` работает.
- Тест: изменение переходов в тестовом YAML меняет поведение без правок кода.
**Вне скоупа:** UI и конкретные шаги процесса.
**Зависит от:** T-001
**Журнал:**
