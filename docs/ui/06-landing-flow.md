# Флоу диаграммы задания (лендинг → регистрация → выбор профиля)

Источник: диаграмма на стр. 5 задания [T] и `flow_trace_template.json` [V5]. Требования: MOCK-1, MOCK-2, MOCK-3, TRC-1, TRC-2. Сценарии: S-09, N-12.
Это **отдельная короткая цепочка**, показывающая стиль интеграции PX ↔ Customer Journey ↔ Resource Catalog. Она создаёт нового партнёра `partners-N` и сохраняет выбранный профиль; личный кабинет (`02-cabinet.md`) работает с партнёром из витрины.

## 6.1 Шаг 1 — лендинг: `GET /qos_platform/landing`
```text
┌──────────────────────────────────────────────────────────────┐
│ Платформа качества связи                                     │
│ Приоритет для вашего трафика                                 │
│                                                              │
│ Компания*   [__________________]                            │
│ Контакт*    [__________________]                            │
│ Трафик      [Видеосвязь ▼]  (описание/объём)                │
│             [Отправить]                                      │
└──────────────────────────────────────────────────────────────┘
```
Реплики 1–4: запрос лендинга → вызов Customer Journey → HTML формы → `200 text/html`.

## 6.2 Шаг 2 — регистрация и выбор профиля: `POST /qos_platform/reg`
Реплики 5–8: форма → CJ → `POST /px/reg` → `{"id": "partners-1"}`. Реплики 9–12: CJ запрашивает `GET /rc/qos_catalog`, строит страницу выбора.
```text
┌──────────────────────────────────────────────────────────────┐
│ Партнёр зарегистрирован: partners-1                          │
│ Выберите QoS-профиль                                         │
│ ( ) Бронза   10 Мбит/с   SLA 99.0 %                          │
│ ( ) Серебро  30 Мбит/с   SLA 99.5 %                          │
│ (•) Золото   50 Мбит/с   SLA 99.9 %                          │
│ ( ) Платина  100 Мбит/с  SLA 99.95 %                         │
│ ( ) Бриллиант 200 Мбит/с  SLA 99.99 %                         │
│ [client_id: partners-1]                      [Подключить]    │
└──────────────────────────────────────────────────────────────┘
```
Список профилей приходит из каталога (`/rc/qos_catalog`), а не из кода.

## 6.3 Шаг 3 — подключено: `POST /qos_platform`
Реплики 13–17: форма (`client_id=partners-1, profile=Gold`) → CJ → `POST /px/save_qos` → `{"id": "qos_profiles-1"}` → HTML.
```text
┌─ ✓ Партнёр подключён ────────────────────────────────────────┐
│ client_id: partners-1                                        │
│ Тариф: Золото · 50 Мбит/с                                    │
│ SLA: 99.9 % (из каталога)                                    │
│ Цена (срок по умолчанию 12 ч): 50 × 100 × 2.0 × 1.0 = 10 000 ₽/мес │
│ [Перейти в личный кабинет] ▸ Трассировка (17 из 17 ✓)         │
└──────────────────────────────────────────────────────────────┘
```
`[Перейти в личный кабинет]` открывает `/cabinet` для `partners-1` (сессия выдаётся по токену витрины).

## 6.4 Соответствие репликам диаграммы
| № | От → Кому | Сообщение | Где в UI/коде |
|---|---|---|---|
| 1 | Service Provider → Partner Landing | `GET /qos_platform/landing` | 6.1 |
| 2 | Partner Landing → Customer Journey | `GET /cj/qos_platform (empty)` | внутренний вызов |
| 3 | Customer Journey → Partner Landing | content: HTML landing | внутренний |
| 4 | Partner Landing → Service Provider | `200 text/html` | 6.1 |
| 5 | Service Provider → Partner Landing | `POST /qos_platform/reg` | 6.1 → 6.2 |
| 6 | Partner Landing → Customer Journey | `POST /cj/qos_platform` | внутренний |
| 7 | Customer Journey → PX | `POST /px/reg` | мок PX |
| 8 | PX → Customer Journey | `200 {"id":"partners-1"}` | мок PX |
| 9 | Customer Journey → Resource Catalog | `GET /rc/qos_catalog` | мок каталога |
| 10 | Resource Catalog → Customer Journey | список профилей | мок каталога |
| 11 | Customer Journey → Partner Landing | content: HTML «выбор QoS-профиля» | 6.2 |
| 12 | Partner Landing → Service Provider | `200 text/html` | 6.2 |
| 13 | Service Provider → Partner Landing | `POST /qos_platform` (client_id, profile) | 6.2 → 6.3 |
| 14 | Partner Landing → Customer Journey | `POST /cj/qos_platform` | внутренний |
| 15 | Customer Journey → PX | `POST /px/save_qos` | мок PX |
| 16 | PX → Customer Journey | `{"id":"qos_profiles-1"}` | мок PX |
| 17 | Customer Journey → Partner Landing | content: HTML «Партнёр подключён» | 6.3 |
В нашей реализации «Partner Landing» и «Customer Journey» — слои одного приложения; каждая реплика записывается в трассировку с номером (`trace_entry`).

## Что проверить при ревью
1. Нужна ли эта цепочка в демо (она дублирует «регистрацию» из PX, которая по заданию вне скоупа) — или показываем её только как доказательство соответствия диаграмме.
2. Нужно ли показывать цену в карточке (V5 показывает SLA; цену в карточку добавляет V5 F7).
3. Поля формы лендинга (company, contact, traffic) — состав и подписи.
4. Связь с основным путём: партнёр `partners-1` попадает в кабинет «пустым» (без услуг), а `mts-link-1` — с готовыми данными.
