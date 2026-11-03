# Доменная модель (v2, по заданию)

Источник: `requirements.md`, `analysis.md`. Партнёр уже зарегистрирован в PX и приходит с `Partner_ID`.

## Сущности
| Сущность | Основные поля | Примечание |
|---|---|---|
| Partner | partner_id (из PX), company, contact, traffic, status | статус — процесс партнёра (ниже) |
| PartnerService | partner, name (напр. «Link ВКС») | FR-2 |
| Signature | service, ipv4, uri, port, protocol | FR-3; protocol из справочника |
| QosProfile | code, name, bandwidth, latency, max_duration, sla, price_rate | **справочник из `config/`** (FR-4), в БД не редактируется |
| ServiceQosAssignment | service, profile, duration_sec | FR-5; duration ≤ max_duration профиля |
| Offer | partner, payload_json, price, status `draft→sent→confirmed` | FR-7, FR-8 |
| SandboxRun | partner, started_at, result `running\|passed\|failed` | FR-9, FR-10 |
| SandboxCheck | run, signature, assignment, result `pending\|passed\|failed`, note | строка на сигнатуру |
| Subscriber | msisdn, tariff, region | seed |
| SubscriberService | subscriber, service, status `pending→active→terminated`, activated_at | FR-13 |
| NetworkRequest | partner, kind (напр. `qod_api_activate`), request_json, response_json, ts | журнал эмулированных вызовов GSMA QoD APIgw, FR-12 |
| AuditEvent | entity, entity_id, action, from_status, to_status, actor, ts | FR-14 |

## Процесс партнёра (`config/process.yaml`)
```
registered ──► configuring ──► offer_requested ──► offer_confirmed ──► sandbox ──► active
                  ▲                                                        │
                  └──────────────── (песочница не пройдена) ───────────────┘
```
- `registered` — пришёл из PX с `Partner_ID`.
- `configuring` — вводит сервисы, сигнатуры, назначает профили и Duration (шаги 3, 6).
- `offer_requested` — JSON отправлен в PX, ждём цену.
- `offer_confirmed` — партнёр подтвердил цену, PX подтвердил продолжение.
- `sandbox` — идёт тестирование (шаг 7).
- `active` — активация выполнена, вызов APIgw залогирован (шаг 8).

Таблица переходов и условия живут в YAML; движок только применяет их и пишет `AuditEvent` (ADR 0003).

## Справочники в `config/`
`protocols.yaml` (RTP, TCP, UDP, HTTP, HTTPS, DNS, IMAP, POP3, SSH), `qos_profiles.yaml`, `process.yaml`, `px_payload.yaml` (маппинг полей JSON для PX), `pricing.yaml`.

## Правила
- Смена статуса — только через движок процесса + `AuditEvent`.
- Любой исходящий «внешний» вызов (PX, APIgw) фиксируется в `NetworkRequest`.
