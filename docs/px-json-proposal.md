# JSON для PX — рабочее предложение v0.1

**Статус: предложение команды, не согласовано с PX.** Официальной спецификации нет (T 2b: «по предоставленной PX спецификации» — ждём). Пока работаем по этому формату; он меняется конфигом (`config/px_payload.yaml`, ADR 0003), так что приход настоящей спеки — правка маппинга, а не кода.

## Принципы
1. **Совместимость с эталоном.** Все поля из `expected_export.json` (V1/V2/V3) остаются на тех же местах и с теми же именами — иначе тесты приёмки V1 A5 / V2 A6 не сойдутся. Новое только **добавляется**.
2. **Плоско и читаемо.** Один документ — одна конфигурация партнёра; вложенность ровно `partner → services → signatures`.
3. **Единицы явные.** Скорость в Мбит/с, срок в часах (код + число), цена в ₽/мес.
4. **Версия формата** в самом документе, чтобы PX мог принять изменение.

## Запрос: конфигуратор → PX (экспорт)
`GET /api/v1/partners/{partner_id}/export` (и тот же объект во `postMessage` `qod:export`).

```json
{
  "schema_version": "0.1",
  "partner_id": "mts-link-1",
  "partner_name": "MTS Link",
  "generated_at": "2026-11-03T12:00:00Z",
  "offer": {
    "offer_id": "offer-1",
    "name": "Базовый",
    "status": "confirmed"
  },
  "services": [
    {
      "service_id": "svc-vcs",
      "name": "Link ВКС",
      "description": "Видеоконференцсвязь MTS Link",
      "qos_profile": {
        "code": "PLATINUM",
        "name": "Platinum",
        "bitrate_mbps": 100,
        "priority_level": 4,
        "sla_percent": 99.95
      },
      "duration": { "code": "12H", "hours": 12 },
      "signatures": [
        { "ipv4": "10.10.1.5", "uri": "vcs.mts-link.ru", "port": 443, "protocol": "HTTPS" },
        { "ipv4": "10.10.1.6", "uri": "media.mts-link.ru", "port": 5004, "protocol": "RTP" }
      ]
    }
  ]
}
```

| Поле | Откуда | Примечание |
|---|---|---|
| `schema_version` | конфиг | **новое**; `0.1` |
| `partner_id`, `partner_name`, `generated_at` | эталон | без изменений |
| `offer` | **новое** | вариант предложения (PROC-4): `status` = `draft` \| `confirmed` |
| `services[].service_id` | **новое** | стабильный ключ сервиса |
| `services[].name`, `description` | эталон | |
| `services[].qos_profile.{code,name,bitrate_mbps,priority_level}` | эталон | |
| `services[].qos_profile.sla_percent` | **новое** | из каталога (V5) |
| `services[].duration.{code,hours}` | эталон | |
| `services[].signatures[].{ipv4,uri,port,protocol}` | эталон | после правок схем могут появиться `ipv6`, `uri` — необязателен |

В экспорт попадают только сервисы с подтверждённым назначением (EXP-2); нет сервисов → `"services": []` (EXP-3).
**Цену в экспорт не кладём:** по заданию её считает PX [T 2b].

## Ответ: PX → конфигуратор (мок)
PX считает предложение по полученному JSON. Мок использует нашу формулу `bitrate_mbps × 100 ₽/мес × price_multiplier`.

```json
{
  "offer_id": "offer-1",
  "currency": "RUB",
  "items": [
    { "service_id": "svc-vcs", "price_rub_per_month": 30000 }
  ],
  "total_price_rub_per_month": 30000,
  "valid_until": "2026-11-10T12:00:00Z"
}
```
Партнёр подтверждает цену → `POST /px/save_qos` (`{client_id, offer_id, accepted: true}`) → `{"id": "qos_profiles-1"}` (флоу V5, реплики 15–16).

## Что в формат НЕ входит
- Payload активации в GSMA QoD APIgw (CAMARA + 3GPP) — отдельный документ/мок (T-009, `domain.md` §5).
- Данные абонентов и подключения (T-010).

## Вопросы, которые закроет настоящая спека PX
1. Имена и вложенность полей; нужен ли `offer` и `schema_version`.
2. Единицы и формат срока (часы/секунды/ISO-8601 duration).
3. Кто задаёт идентификаторы (`service_id`, `offer_id`) — мы или PX.
4. Нужны ли в экспорте URI/protocol (они не ложатся на CAMARA, см. analysis §6).
