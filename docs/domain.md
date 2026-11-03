# Доменная модель (v1, уточнить по ТЗ)

| Сущность | Поля (основное) | Статусы |
|---|---|---|
| Partner | name, inn, type (MVNO / контент-провайдер / B2B-интегратор), contact, api_key | `draft → submitted → in_review → approved \| rejected` |
| OnboardingStep / Document | partner, step, done, документы-заглушки | — |
| ConnectionScheme | name, description, параметры, требования (справочник) | — |
| PartnerConnection | partner, scheme, params (endpoint, IP whitelist) | `requested → configured → active` |
| ServiceProduct | name, qos_profile (текст/JSON) | — |
| Subscriber | msisdn, tariff, region (seed) | — |
| SubscriberService | subscriber, product, partner, activated_at | `pending → active → suspended \| terminated` |
| AuditEvent | entity, entity_id, action, from/to status, actor, timestamp | — |

Правило: любая смена статуса идёт через сервис и порождает `AuditEvent`.
Примеры продуктов: «Приоритет QoS для видео», «Гарантированная скорость», «Low latency для игр».
