# T-008: Песочница

**Цель:** SBX-1…SBX-6, SBX-8.
**Данные:** `v4/test_data/seed.json`, `demo_scenario.json`, `expected_event_log.json`.
**Файлы:** `app/models.py` (TestRun, TestStep, EventLog), `app/services/sandbox.py`, `app/web/sandbox.py`, `app/templates/sandbox/*`, тесты.
**Критерии приёмки:**
- Автомат Draft → InTesting → Passed/Failed → Applied; недостижимые статусы недоступны.
- Прогон строится по сигнатурам; проверка строки, галка подтверждения; Failed при любом error, Passed при всех success+confirmed.
- Любая правка сигнатуры/назначения вне Draft/Applied сбрасывает в Draft, прежние шаги не переносятся; в Applied правка отклонена с записью в журнал.
- Журнал совпадает по последовательности с `expected_event_log.json` (V4 A1–A5, A7, A8).
**Вне скоупа:** мок APIgw (T-009).
**Зависит от:** T-002
**Журнал:**
