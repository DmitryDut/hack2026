# Доска задач

Статусы: `todo` · `in_progress` · `done`. ID требований — из [requirements.md](../requirements.md). Тестовые данные — `docs/source/zadanie/tz/*/test_data/`; в карточках `v1…v5` = `variant_1_crud_inventory` … `variant_5_px_showcase_iframe`.

| ID | Задача | Итер. | Требования | Зависит от | Статус | Агент | Ветка |
|---|---|---|---|---|---|---|---|
| T-000 | Каркас проекта и настройки агентов | 0 | NFR-2, NFR-6 | — | done | claude | main |
| T-DOCS | Разбор задания, требования, бэклог | 0 | — | T-000 | done | claude | main |
| T-001 | Ядро: `entity_defs`/`entities`, универсальный CRUD, валидация по JSON Schema | 1 | CORE-1…4, CORE-8 | T-000 | todo | | |
| T-002 | Справочники, стартовые схемы, сид `mts-link-1`, валидации данных | 1 | DATA-1…9, CORE-4 | T-001 | todo | | |
| T-003 | Рендерер форм/списков по схеме + админка схем | 2 | CORE-5…7 | T-001 | todo | | |
| T-004 | Связи и экспорт JSON для PX, цена, варианты предложения | 2 | EXP-1…5, CORE-9, PROC-1…5 | T-002 | todo | | |
| T-005 | Моки PX и каталога, карточка «Партнёр подключён» | 2 | MOCK-1…3, STD-1 | T-002 | todo | | |
| T-006 | Встраивание: HMAC-токен, iframe, `postMessage`, CSP, фолбэк | 3 | EMB-1…6, NFR-4 | T-005 | todo | | |
| T-007 | Трассировка 17 реплик + панель | 3 | TRC-1, TRC-2 | T-005 | todo | | |
| T-008 | Песочница: автомат, TestRun/TestStep, сброс при правках, EventLog | 3 | SBX-1…6, SBX-8, NFR-3 | T-002 | todo | | |
| T-009 | Мок GSMA APIgw (validate, sessions), активация, изоляция по партнёру | 3 | SBX-7, SBX-9, SBX-10, STD-2, STD-3 | T-008 | todo | | |
| T-010 | Подключение абоненту (QoS Provisioning) + карточка абонента | 4 | SUB-1…3 | T-009 | todo | | |
| T-011 | Сценарий «поменяйте вот это» + `docs/change-playbook.md` | 4 | NFR-1 | T-003, T-004 | todo | | |
| T-012 | E2E-тест демо, `make demo`, полировка, README | 4 | NFR-5…7 | T-006…T-011 | todo | | |
| T-013 | (опция) AI-агент: чат, tool calls, фолбэк | — | AI-1 | T-002 | todo | | |

Критический путь: T-001 → T-002 → T-004 → T-011 (главный критерий оценки). Параллельно после T-002: T-003, T-004, T-005, T-008.
