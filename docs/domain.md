# Доменная модель (v3)

Источник: `requirements.md`, `analysis.md`, V1/V2/V4 `test_data`. Конфигурируемые сущности хранятся универсально, фиксированы только служебные.

## 1. Конфигурируемые сущности (CORE-1…CORE-9)
Хранение: `entity_defs {type, title, schema (JSON Schema), updated_at}` и `entities {id, type, data (JSON), created_at, updated_at}`. Схемы правятся через админку; код про конкретные типы не знает.

Стартовые типы (из V2 `entity_schemas.json`, `seed_entities.json`):
| Тип | Основные поля |
|---|---|
| partner | partner_id (напр. `mts-link-1`), name, status (`active\|draft`) |
| service | name, description, partner_ref, qos_profile_code, duration_code, assignment_status (`draft\|confirmed`) |
| signature | ipv4, uri, port (1–65535), protocol (enum из справочника), service_ref |
| qos_profile | code, name, bitrate_mbps, priority_level, price_multiplier, sla_percent |
| duration | code (`1H…72H`), hours, price_multiplier (коэффициент срока: 0.15 / 0.6 / 1.0 / 1.7 / 4.0) |

Справочники (`protocol`, `qos_profile`, `duration`) — тоже сущности, т.е. «новый тариф» = новая запись. Связи для экспорта — конфиг `relations.json`: `partner → service → signature`, поле связи и поля вывода заданы данными.
Правки по ТЗ (V2 `demo_change.json`): `ipv6` в signature, `uri` необязателен, `sla_percent` (99–99.999) в service, новая сущность `monitoring`.

## 2. Процесс сервиса (SBX-1…SBX-10)
Статус конфигурации сервиса — автомат V4:
```
Draft ─start─► InTesting ─все шаги success+confirmed─► Passed ─apply─► Applied
  ▲                │
  └──reset─────────┴─ любой шаг error ─► Failed
  ▲
  └── любое изменение сигнатуры/назначения в InTesting/Passed/Failed
Applied: изменения запрещены; выход только явным сбросом оператора (в журнал)
```
Служебные сущности (фиксированы в коде):
| Сущность | Поля |
|---|---|
| TestRun | id, service_id, status (`draft\|in_testing\|passed\|failed\|applied`), started_at, finished_at |
| ServiceState | service_id, status (то же), session_id, applied_at, expires_at — признак приоритета вычисляется из `applied` и `expires_at` (`SPEC.md` D16) |
| TestStep | id, test_run_id, signature_id, result (`pending\|success\|error`), confirmed_by_user, checked_at, error_message |
| EventLog | id, entity_type, entity_id, event, details, created_at |
| NetworkRequest | id, kind (`px_reg`, `px_save_qos`, `rc_catalog`, `gsma_validate`, `gsma_session`, `qos_assignment`), request_json, response_json, ts — журнал вызовов моков |
| TraceEntry | seq (1–17), from, to, message, ts — трассировка флоу V5 |

## 3. Процесс партнёра и цена (PROC-1…PROC-5)
- Шаги процесса партнёра и их порядок — конфиг `process` (по умолчанию: анкета → сервисы/сигнатуры → профиль и срок → цена → подтверждение → тест → включение).
- Цена: конфиг формулы; по умолчанию `bitrate_mbps × 100 × price_multiplier` (₽/мес).
- Вариант предложения (PROC-4): набор «сервис + профиль + Duration + цена» с названием; у партнёра несколько вариантов, один выбирается для отправки.

## 4. Абонент (SUB-1…SUB-3)
| Сущность | Поля |
|---|---|
| Subscriber | msisdn, tariff, region (seed) |
| QosAssignment | id, subscriber, service, qos_profile, status (`REQUESTED\|AVAILABLE\|UNAVAILABLE`), created_at |

## 5. Соответствие стандартам (STD-1…STD-3)
| Наше | CAMARA | 3GPP |
|---|---|---|
| qos_profile.code / name | `QosProfile.name` | `qosReference` |
| bitrate_mbps | `max{Up,Down}streamRate {value, unit: Mbps}` | — |
| duration.hours | `duration` (сек) = hours × 3600; `minDuration/maxDuration` | `qosDuration` |
| signature.ipv4 | `applicationServer.ipAddresses` (≤16) | `flowInfo`/`flowDescriptions` |
| signature.port | `applicationServerPorts.ports` | `flowDescriptions` |
| signature.uri | — | PFD `urls` / `domainNames` |
| signature.protocol | — | PFD `flowDescriptions`, `dnProtocol` |
| QosAssignment | `POST /qos-assignments {device.phoneNumber, qosProfile}` | — |

## 6. Правила
- Валидация данных — по JSON Schema типа; серверная и в форме совпадают.
- Смена статуса `TestRun` — только через сервис автомата + запись `EventLog`.
- Каждый вызов мока пишется в `NetworkRequest`.
- Изоляция: сервисы фильтруются по `partner_id` (заголовок `X-Partner-Id`).
