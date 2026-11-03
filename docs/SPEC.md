# Спецификация реализации (для разработки любым агентом)

Документ самодостаточен: по нему и `requirements.md` можно писать код, не зная истории чата. Если спецификация противоречит `requirements.md`, прав `requirements.md` — и спецификацию нужно исправить. Источники тестовых данных (`V1…V5`) лежат в `docs/source/zadanie/tz/variant_N_*/test_data/`.

Статус: **v1.1, 2026-11-03** (учтены макеты v2: личный кабинет, вход, цена со сроком, признак приоритета). Кода пока нет, кроме каркаса (`app/main.py`, `app/db.py`, `/health`, главная страница).

## 1. Принятые решения
| # | Решение | Откуда |
|---|---|---|
| D1 | Стек: FastAPI, SQLModel/SQLite, Jinja2 + HTMX + Pico.css, `jsonschema`, `pyyaml`; `uv`, `ruff`, `pytest`. Node не нужен | ADR 0001, 0003 |
| D2 | Один процесс: витрина-мок PX и личный кабинет — разные страницы одного приложения | требование EMB-6 |
| D3 | Модель данных — JSON Schema в БД; формы и CRUD универсальны | ADR 0003 |
| D4 | Процесс партнёра, цена, маппинг JSON для PX, правила мока — YAML в `config/` | ADR 0003 |
| D5 | **Отменено 2026-11-03:** подключение услуги к конечному абоненту не делаем — платформа работает с партнёрами | решение пользователя |
| D6 | AI-агент не делаем | AI-1 |
| D7 | **Ссылки между сущностями — расширение схемы `x-ref`** (см. §5): профиль, Duration, протокол — записи справочников, а не `enum` в схеме. Иначе «добавить Diamond» потребовало бы править схемы. Это отклонение от стартовых схем V2, оно совместимо с их тестами | наше решение |
| D8 | Статус песочницы хранится не в сущности `service`, а в служебной таблице `service_state` — админка схем не должна уметь его сломать | наше решение |
| D9 | Сервис имеет поле `assignment_status` (`draft`/`confirmed`): в экспорт идут только `confirmed` (V1 F7) | V1 |
| D10 | Два набора данных: демо-сид (на основе V4, 4 сигнатуры у «Link ВКС») и фикстура контрактных тестов экспорта (на основе V1, 3 сигнатуры). Их значения расходятся, поэтому тест экспорта грузит свою фикстуру | расхождение V1 и V4 |
| D11 | JSON для PX — `px-json-proposal.md`; цену в экспорт не кладём | EXP-5 |
| D12 | Цена — произведение множителей из конфига, без `eval` | наше решение |
| D13 | **Вход партнёра:** форма `/login` (мок авторизации, логин/пароль-заглушка из `config/accounts.yaml`); сессия — cookie с тем же HMAC-токеном, что и вход из витрины (`/embed?token=` создаёт сессию без формы). Реальной аутентификации нет | решение пользователя, макеты `ui/00-login.md` |
| D14 | **Партнёрский интерфейс — личный кабинет** (`/cabinet*`): главная со списком услуг и карточка услуги с вкладками (данные → тариф и стоимость → тестирование → запуск); вкладки и условия доступа — `config/process.yaml` | решение пользователя, `ui/02-cabinet.md` |
| D15 | **Срок влияет на цену:** коэффициент срока `duration.price_multiplier` (12 ч = 1.0, чтобы пример задания «Платиновый на 12 часов = 30 000 ₽/мес» сохранился): 1 ч — 0.15, 6 ч — 0.6, 12 ч — 1.0, 24 ч — 1.7, 72 ч — 4.0 (рабочие значения, меняются записью справочника). Единица цены остаётся «₽/мес», как в задании | предложено командой для POC, подтверждено пользователем |
| D18 | **Гибридная модель (P1):** встроенные типы (тариф, срок, услуга, сигнатура) остаются таблицами; поля, добавленные в JSON-схему, хранятся в колонке `extra`; новые типы из редактора схем — в универсальной таблице `Entity`. Схемы — в `EntityDef`, стартовые — `config/schemas/*.json`. Упрощение относительно D3: см. TD-026 | реализация P1 |
| D17 | **Корпоративный стиль МТС:** тема `app/static/theme.css` (CSS-переменные поверх Pico.css) с токенами из `docs/ui/brand.md` (референс mws.ru, светлая тема); цвета и шрифты берутся только из токенов; логотип — официальный SVG без изменений; шрифты — локальный `@font-face` (файлы вне git) с заменой на Arial | NFR-8, решение пользователя |
| D16 | **Признак приоритета** — вычисляется при показе: услуга `applied` и `expires_at` в будущем → «⚡ приоритет активен до …»; после срока — «⏱ срок истёк» (статус в БД не меняется). Отражает данные APIgw (мок), не измеряет трафик | решение пользователя |

## 2. Структура репозитория (целевая)
```text
app/
  main.py                 # создаёт приложение, подключает роутеры, CSP-заголовки
  config.py  db.py        # есть
  config_loader.py        # читает config/*.yaml|json, валидирует при старте
  models.py               # EntityDef, Entity, ServiceState, TestRun, TestStep, EventLog, NetworkRequest, TraceEntry
  services/               # вся бизнес-логика (см. §4)
    schema_core.py  data_rules.py  form_render.py  export.py  pricing.py  offer.py  priority.py
    sandbox.py  activation.py  token.py  auth.py  trace.py  audit.py
  api/                    # тонкие JSON-роуты: entities.py schemas.py export.py sandbox.py ...
  web/                    # тонкие HTML-роуты: auth.py cabinet.py entities.py admin_schemas.py px_showcase.py embed.py landing.py operator.py
  mocks/                  # px.py resource_catalog.py gsma_qod.py qos_provisioning.py
  templates/  static/     # static/theme.css (токены бренда), static/brand/ (логотип), static/fonts/ (вне git)
config/
  schemas/*.json          # стартовые JSON Schema: partner service signature qos_profile duration protocol 
  relations.json  process.yaml  pricing.yaml  px_payload.yaml  mock_rules.yaml  protocols.yaml  accounts.yaml
scripts/seed.py           # демо-сид: загрузка схем, справочников и данных (идемпотентно)
tests/                    # unit, api, contract, e2e; tests/fixtures/ (копии нужных test_data)
```
Слои: `web`/`api` → `services` → `models`. Роуты тонкие. Смену статуса `TestRun`/сервиса делает только `services/sandbox.py`.

## 3. Конфиги (`config/`)
Читаются при старте и по кнопке «перечитать конфиг» в админке (`POST /admin/config/reload`); ошибка формата → понятное сообщение, приложение не стартует (при старте) или прежний конфиг остаётся (при перечитывании).

### `process.yaml` — вкладки карточки услуги и условия доступа
```yaml
tabs:                              # порядок = порядок вкладок
  - {id: data,   title: "Данные услуги"}
  - {id: tariff, title: "Тариф и стоимость"}
  - {id: test,   title: "Тестирование"}
  - {id: launch, title: "Запуск"}
gates:                             # условие доступности вкладки; список = «И»
  test:   [has_signatures, price_confirmed]
  launch: [test_passed]
```
Условия (`gates`) — фиксированный набор предикатов над услугой: `has_signatures` (есть ≥1 сигнатура), `tariff_set` (выбраны тариф и срок), `price_confirmed` (`assignment_status = confirmed`), `test_passed` (состояние песочницы `passed` или `applied`), `priority_on` (`applied`). Вкладку без условия можно открыть всегда. Недоступная вкладка серая, подсказка — «почему» (текст по предикату). Перенос условия с одной вкладки на другую — правка YAML (сценарий C-06). Главное меню кабинета (Услуги, Стоимость и предложение, Абоненты, Журнал) задано в коде.

### `pricing.yaml`
```yaml
currency: RUB
unit: per_month
factors:                          # цена = произведение
  - {field: qos_profile.bitrate_mbps}
  - {const: 100}
  - {field: qos_profile.price_multiplier}
  - {field: duration.price_multiplier}
```
`field` — путь `<тип>.<поле>` относительно услуги; значения берутся из записей, на которые ссылаются `service.qos_profile_code` и `service.duration_code`. Цена услуги = произведение; сумма предложения — сумма по услугам.
Примеры (Мбит/с × 100 ₽ × коэффициент тарифа × коэффициент срока): Платина 12 ч = 100 × 100 × 3.0 × 1.0 = **30 000**; Золото 12 ч = 10 000; Золото 24 ч = 10 000 × 1.7 = 17 000; Серебро 12 ч = 4 500; Платина 24 ч = 51 000; Платина 1 ч = 4 500; Бриллиант 12 ч = 80 000.

### `accounts.yaml` — демо-учётки (мок авторизации)
```yaml
session_ttl_hours: 8              # в iframe витрины токен живёт 1 час
show_demo_hint: true              # показывать блок «демо-доступ» на /login
accounts:
  - {login: mts-link-1,    password: demo, role: partner,  partner_id: mts-link-1,    name: "MTS Link"}
  - {login: other-partner, password: demo, role: partner,  partner_id: other-partner, name: "Другой партнёр"}
  - {login: operator,      password: demo, role: operator, name: "Оператор"}
```
Пароли — заглушки для демо (репозиторий публичный: реальных секретов в нём нет и быть не должно).

### `px_payload.yaml` — маппинг JSON для PX (формат `px-json-proposal.md`)
```yaml
schema_version: "0.1"
partner:  {fields: {partner_id: partner_id, partner_name: name}}
offer:    {fields: {offer_id: id, name: name, status: status}}
service:
  fields: {service_id: id, name: name, description: description}
  lookups:
    qos_profile: {from: qos_profile_code, entity: qos_profile, key: code,
                  fields: [code, name, bitrate_mbps, priority_level, sla_percent]}
    duration:    {from: duration_code, entity: duration, key: code, fields: [code, hours]}
signature: {fields: [ipv4, uri, port, protocol]}      # необязательные поля выводятся, если присутствуют
```
Верхний уровень выхода: `schema_version`, `partner_id`, `partner_name`, `generated_at`, `offer`, `services[]`. Добавление поля в JSON для PX = строка в `fields`.

### `relations.json` (V2 `relations.json` + `on_delete`)
Дерево `partner → service (partner_ref → partner_id, cascade) → signature (service_ref → id, cascade)`; тот же формат, что в V2, плюс `"on_delete": "cascade"` на каждом ребёнке.

### `mock_rules.yaml` — поведение мока проверки
```yaml
validate:
  rules:
    - match: {uri: media2.mts-link.ru, port: 5005}
      result: error
      error_code: BEARER_TIMEOUT
      message: "RTP-поток не отвечает: таймаут установки dedicated bearer для media2.mts-link.ru:5005"
  default: {result: success}
  latency_ms: [300, 800]      # диапазон имитируемой задержки
```
Правило срабатывает по значениям сигнатуры (после правки порта на 5006 — success).

### `protocols.yaml`
Каждый протокол: `code`, `layer` (`transport`/`application`), `transport` (`tcp`/`udp`) — нужен для PFD (`RTP→udp`, `HTTP/HTTPS/IMAP/POP3/SSH→tcp`, `DNS→udp`).

## 4. Данные
### Универсальные (конфигурируемые) сущности
Таблицы `entity_def(type PK, title, schema JSON, updated_at)` и `entity(id PK str, type, data JSON, created_at, updated_at)`. Типы и стартовые схемы — `config/schemas/`; загружаются сидом, дальше живут в БД.
Типы: `partner`, `service`, `signature`, `qos_profile`, `duration`, `protocol`, `offer`.

Ключевые поля (полные схемы — в `config/schemas/*.json`):
| Тип | Поля |
|---|---|
| partner | `partner_id`*, `name`*, `status` (`active`/`draft`) |
| service | `name`*, `description`, `partner_ref`*, `qos_profile_code` (x-ref qos_profile.code), `duration_code` (x-ref duration.code), `assignment_status` (`draft`/`confirmed`, default `draft`), `offer_ref` |
| signature | `service_ref`*, `ipv4`* (format ipv4), `uri`*, `port`* (1–65535), `protocol`* (x-ref protocol.code) |
| qos_profile | `code`*, `name`*, `bitrate_mbps`*, `priority_level`* (1–5), `price_multiplier`*, `sla_percent`*, `status` (`ACTIVE`/`INACTIVE`/`DEPRECATED`, default ACTIVE) |
| duration | `code`*, `hours`* (≥1), `price_multiplier`* (коэффициент срока, см. D15) |
| protocol | `code`*, `layer`, `transport` |
| offer | `partner_ref`*, `name`*, `service_refs` (array of string), `status` (`draft`/`confirmed`), `price_rub_per_month` |
`*` — required. Стартовые id берём из V4 (`svc-vcs`, `svc-chat`, `sig-1…sig-5`), справочники — из V1/V2/V5.

### Служебные таблицы (в коде)
| Таблица | Поля |
|---|---|
| service_state | `service_id` PK, `status` (`draft/in_testing/passed/failed/applied`), `session_id`, `applied_at`, `expires_at` (из ответа мока сессий) |
| test_run | `id`, `service_id`, `status`, `started_at`, `finished_at` |
| test_step | `id`, `test_run_id`, `signature_id`, `result` (`pending/success/error`), `confirmed_by_user`, `checked_at`, `error_code`, `error_message` |
| event_log | `id`, `entity_type`, `entity_id`, `event`, `details` JSON, `created_at` |
| network_request | `id`, `kind`, `method`, `path`, `request` JSON, `response` JSON, `status_code`, `created_at` |
| trace_entry | `id`, `session` (идентификатор прохода флоу), `seq` 1–17, `from_`, `to`, `message`, `created_at` |

`network_request.kind`: `px_reg`, `px_save_qos`, `rc_catalog`, `gsma_validate`, `gsma_session`, `qos_assignment_create`, `qos_assignment_get`.

## 5. Ядро схем (`schema_core.py`)
Поддерживаемое подмножество JSON Schema (draft-07): `type` (`string`, `integer`, `number`, `boolean`, `object`, `array` of string), `enum`, `minimum`, `maximum`, `minLength`, `pattern`, `format` (`ipv4`, `ipv6` — проверяются модулем `ipaddress`), `required`, `default`, `title`, `description`. Остальное — не гарантируется (рендерер игнорирует, валидатор применит).
Наши расширения (не стандарт, хранятся в той же схеме):
- `"x-ref": "<тип>.<поле>"` — значение должно существовать в записях типа; в форме — выпадающий список из этих записей (подпись — `name` или код). Нарушение → 422 «значение не найдено в справочнике».
- `"x-unique": [["service_ref","ipv4","uri","port","protocol"]]` — комбинации полей, уникальные среди записей типа; нарушение → **409**.
- `"x-readonly": true` — поле не редактируется в форме (id, служебные).
Правила:
- Сохранение схемы: проверить как JSON Schema (`Draft7Validator.check_schema`) и наши расширения; ошибка → 422, прежняя схема сохраняется.
- Создание/правка записи: валидировать по схеме типа (+ `x-ref`, `x-unique`); неизвестный тип → 404; ошибка → 422 `{"detail":[{"field":"port","message":"..."}]}`.
- Чтение записей, созданных по старой схеме, **не валидирует** (CORE-8).
- Удаление: по `relations.json` каскадом удаляются дети; удаление сервиса удаляет сигнатуры и его `service_state`.
- Любое изменение сигнатуры/назначения сервиса вызывает `sandbox.on_config_changed(service_id)` (§8).
- Запись, ссылающаяся на несуществующего родителя (`service_ref`) → 422.

## 6. HTTP API
Префикс JSON: `/api/v1`. Заголовок `X-Partner-Id` обязателен для партнёрских эндпоинтов (помечены **P**): запись другого партнёра → 404. Эндпоинты без P — «админ/справочники» (в демо без аутентификации).

### Вход (HTML-формы, без префикса `/api/v1`)
| Метод и путь | Назначение | Коды |
|---|---|---|
| `GET /login` | страница входа | 200 |
| `POST /login` | `login`, `password` → cookie `qod_session` (HttpOnly, SameSite=Lax; значение — HMAC-токен §10); партнёр → 303 `/cabinet`, оператор → 303 `/operator` | 303, 401 (форма с ошибкой) |
| `GET/POST /logout` | удаляет cookie → 303 `/login` | 303 |
Без сессии `/cabinet*` и партнёрские API → 303 `/login` (HTML) или 401 (JSON). `X-Partner-Id` для кабинета берётся из сессии; прямые API-запросы передают его заголовком.

### Ядро
| Метод и путь | Назначение | Коды |
|---|---|---|
| `GET /schemas` | список схем | 200 |
| `GET/PUT /schemas/{type}` | чтение / замена схемы (PUT создаёт новый тип) | 200, 422 |
| `GET /entity/{type}` | список (`?filter_field=value`) | 200, 404 |
| `POST /entity/{type}` | создать | 201, 404, 409, 422 |
| `GET/PUT/DELETE /entity/{type}/{id}` | чтение / правка / удаление (каскад) | 200/204, 404, 409, 422 |
| `POST /admin/config/reload` | перечитать YAML | 200, 422 |

### Партнёр, экспорт, цена, предложения
| Метод и путь | Назначение |
|---|---|
| `GET /partners/{partner_id}/export` **P** | JSON для PX (`px-json-proposal.md`): только `assignment_status = confirmed` |
| `GET /partners/{partner_id}/services` **P** | сервисы партнёра с сигнатурами и состоянием песочницы |
| `GET /services/{id}/price` **P** | цена сервиса по `pricing.yaml` |
| `POST /partners/{partner_id}/offers` **P** | создать вариант `{name, service_refs}`; `GET` — список; `GET /offers/{id}` — состав, цена |
| `POST /offers/{id}/confirm` **P** | подтвердить цену (`status=confirmed`; `service.assignment_status=confirmed`) |

### Песочница и активация (все **P**)
| Метод и путь | Эффект |
|---|---|
| `GET /services/{id}/sandbox` | состояние: `status`, текущий `test_run`, шаги, `session_id` |
| `POST /services/{id}/sandbox/start` | только из `draft` и подтверждённой цены → `in_testing`, создаёт шаги по сигнатурам |
| `POST /services/{id}/sandbox/steps/{signature_id}/check` | вызов мока валидации; error → шаг `error`, прогон `failed` |
| `POST /services/{id}/sandbox/steps/{signature_id}/confirm` | галка (только для `success`) |
| `POST /services/{id}/sandbox/back` | `failed → draft` (кнопка «Вернуться к конфигурированию») |
| `POST /services/{id}/sandbox/apply` | только из `passed`: вызов мока сессий → `applied`, `session_id` |
| `POST /services/{id}/sandbox/operator-reset` | `applied → draft`, тело `{confirm: true}`; событие `applied_reset` |
Недопустимый переход → 409 `{"detail":"недопустимый переход: <from> → <действие>"}`.

### Моки внешних систем (без `X-Partner-Id`)
| Метод и путь | Контракт |
|---|---|
| `GET /rc/qos_catalog` | `{profiles:[{code,name,bitrate_mbps,sla_percent,price_multiplier}], durations:[{code,hours}], protocols:[code…]}` из сущностей (формат V5 `qos_catalog.json`) |
| `POST /px/reg` | тело `{company, contact, traffic}` → `{"id":"partners-N"}`; создаёт сущность `partner` (`partner_id=partners-N`) |
| `POST /px/save_qos` | `{client_id, profile}` → `{"id":"qos_profiles-N"}` |
| `POST /px/price` | тело — экспорт (`px-json-proposal.md`) → `{offer_id, currency, items:[{service_id, price_rub_per_month}], total_price_rub_per_month, valid_until}` по `pricing.yaml` |
| `POST /mock-gsma/validate` | запрос/ответ по V4 `mock_apigw_contract.json`; решение — `mock_rules.yaml`; `result=error` приходит с HTTP 200 |
| `POST /mock-gsma/qod/sessions` | запрос V4 + блоки `camara` и `pfd` (см. §9) → 201 `{session_id:"qod-session-<6hex>", status:"ACTIVE", started_at, expires_at, qos_profile}` |
Каждый вызов мока платформа пишет в `network_request` (мок сам не пишет — пишет вызывающая сторона, чтобы журнал был один).

## 7. Страницы (HTML, Jinja2 + HTMX)
Макеты экранов — `docs/ui/` (v2, согласованы по образу результата); реализуемые сценарии — `docs/scenarios.md`.
| Путь | Содержимое |
|---|---|
| `/` | входная страница, ссылки на витрину, вход, оператора, админку схем |
| `/login`, `/logout` | вход партнёра и оператора (мок, D13), блок «демо-доступ», кнопка «Войти как оператор» |
| `/px-showcase` | витрина-мок PX: страница партнёра `mts-link-1`, кнопка «Конфигурировать сервисы QoS» открывает iframe `/embed?token=…` (токен выдаёт сервер), «Открыть в новой вкладке», карточка «Партнёр подключён» (с признаком ⚡ по услугам партнёра) после `postMessage`, панель «Трассировка» |
| `/embed?token=…` | проверка токена → создаёт сессию → переход в `/cabinet?embed=1` (шапка сайта скрыта); плохой токен → страница ошибки |
| `/cabinet` | главная кабинета: баннер приоритета (⚡ N из M услуг), таблица услуг (тариф, срок, стоимость, статус/приоритет), итоги стоимости |
| `/cabinet/services/new`, `/cabinet/services/{id}?tab=data\|tariff\|test\|launch` | форма услуги; карточка услуги с вкладками из `process.yaml`: сигнатуры; тариф и расчёт стоимости; песочница; запуск, панель «⚡ Трафик приоритизирован» и результаты теста |
| `/cabinet/offer` | стоимость и предложение: услуги, итоги, варианты и сравнение, JSON для PX, «Отправить в витрину PX» |
| `/cabinet/journal` | журналы событий и внешних вызовов партнёра |
| `/qos_platform/landing`, `POST /qos_platform/reg`, `POST /qos_platform`, `/cj/qos_platform` | флоу диаграммы V5, шаги 1–3 (§10) |
| `/entities/{type}` | универсальные список + форма по схеме |
| `/admin/schemas` | выбор типа, редактор JSON Schema, сохранение (PUT), создание типа, кнопка «перечитать конфиг» |
| `/operator` | партнёры и статусы, журнал событий, журнал внешних вызовов (запрос/ответ JSON) |
| `/mock-px?partner_id=` | страница предложения V1 F9 (цена по формуле) — допустимо реализовать как вид `/px-showcase` |
Тексты UI — на русском. HTMX — для частичных обновлений (проверка шага, подтверждение).

### Рендерер форм (`form_render.py`)
Вход — схема типа; выход — описание полей. Соответствие: `string` → text; `string`+`enum` → select; `x-ref` → select из записей; `integer`/`number` → number с `min`/`max`; `boolean` → checkbox; `required` → обязательное; `title` → подпись; `x-readonly` → не редактируется. Колонки таблицы — свойства схемы в порядке объявления. Серверные сообщения 422 выводятся под полем.

## 8. Бизнес-правила
### Валидация сигнатур
IPv4 — 4 октета 0–255; порт 1–65535 (целое); протокол — запись справочника; `uri` — непустая строка (необязательна, если так сказано в схеме); дубликат → 409. Тестовые кейсы — V1 `invalid_signatures.json`.

### Автомат песочницы (`sandbox.py`)
Состояния: `draft`, `in_testing`, `passed`, `failed`, `applied`.
| Из | Действие | В | Событие (`event_log.event`) |
|---|---|---|---|
| draft | start (выполнены `gates` вкладки «Тестирование»: по умолчанию цена подтверждена и есть ≥1 сигнатура) | in_testing | `run_started` (details: `service_id`, `steps_created`, `from_status`, `to_status`) |
| in_testing | check шага → success | in_testing | `step_checked` (`signature_id`, `result`) |
| in_testing | check шага → error | failed | `step_checked` (+`error_code`), затем `run_failed` (`reason: step_error`) |
| in_testing | confirm шага | in_testing | `step_confirmed` (`signature_id`, `by_user: true`) |
| in_testing | все шаги success и confirmed | passed | `run_passed` |
| failed | back | draft | `run_reset` (`reason: user_back`) |
| in_testing / passed / failed | любая правка сигнатуры или назначения | draft | `run_reset` (`reason: signature_modified`, `signature_id`), затем `signature_updated` (`changes: {поле: {old,new}}`); шаги старого прогона не переносятся |
| passed | apply | applied | `applied_to_production` (`service_id`, `session_id`, `from_status`, `to_status`) |
| applied | любая правка | applied | `change_rejected` (`reason: applied_locked`), API → 409 |
| applied | operator-reset | draft | `applied_reset` |
Любой иной переход → 409. Порядок записей в журнале должен совпадать с V4 `expected_event_log.json` (последовательность `event` и `entity_type`).
Шаги проверяются в любом порядке, но подтверждение возможно только после `success`. Правка сигнатуры в `draft` — обычная, событие `signature_updated`.

### Цена, предложение
Цена услуги = Мбит/с × 100 ₽ × коэффициент тарифа × коэффициент срока (`pricing.yaml`, D15); при смене тарифа или срока цена пересчитывается, а подтверждение (`assignment_status`) сбрасывается в `draft`. Предложение — набор сервисов партнёра с профилем и Duration; `POST /offers` считает цену по `pricing.yaml`. `confirm` без профиля/Duration у какого-либо сервиса → 422. Подтверждённое предложение переводит его сервисы в `assignment_status = confirmed`. Правка назначения возвращает `assignment_status` в `draft` и сбрасывает песочницу по правилу выше.

### Признак приоритета (`priority.py`)
Функция `priority_view(service)` возвращает `off` / `on` (с `expires_at`, остатком времени, списком сигнатур, `session_id`) / `expired`. Правило: `on` — состояние `applied` и `expires_at > now`; `expired` — `applied` и срок прошёл; иначе `off`. Используется кабинетом (баннер, строка, панель), витриной и оператором — одним источником (NFR-3, SBX-11).

## 9. Payload активации и соответствие стандартам
Тело `POST /mock-gsma/qod/sessions` — V4 контракт (`partner_id`, `service`, `qos_profile{code,bitrate_mbps}`, `duration{code,hours}`, `signatures[]`) **плюс** блоки, формируемые платформой (иллюстративно, мок их не проверяет):
```json
"camara": {
  "qosProfile": "PLATINUM",
  "duration": 43200,
  "applicationServer": {"ipAddresses": ["10.10.1.5", "10.10.1.6"]},
  "applicationServerPorts": {"ports": [443, 5004]}
},
"pfd": {
  "flowDescriptions": ["permit out 6 from 10.10.1.5 443 to any", "permit out 17 from 10.10.1.6 5004 to any"],
  "urls": [], "domainNames": ["vcs.mts-link.ru", "media.mts-link.ru"]
}
```
Правила: `duration` = `hours × 3600`; ≤16 уникальных IP (иначе 422 при активации); номер протокола из `protocols.yaml` (`tcp`→6, `udp`→17); формат `flowDescriptions` — упрощённый IPFilterRule, **не** проверяется на соответствие TS 29.212. Точные поля 3GPP — `docs/source/zadanie/TS29122_PfdManagement.yaml`, `TS29122_AsSessionWithQoS.yaml`; CAMARA — `docs/source/camara/*`.

## 10. Витрина, токен, трассировка
### Токен (V5 `token_test_vectors.json`)
`token = b64url(payload).b64url(hmac_sha256(b64url(payload), PX_SECRET))`, `payload = {"partner_id", "expires_unix"}` (JSON без пробелов). Секрет — переменная `PX_SECRET` (демо: `hackathon-demo-secret`). Сравнение подписей — `hmac.compare_digest`. Ошибки: формат/подпись → «токен недействителен»; срок → «срок действия истёк». Страница ошибки не обращается к данным партнёра.

### Сессия
Cookie `qod_session` хранит тот же HMAC-токен (`partner_id`, `role`, `expires_unix`). Выдаётся при `POST /login` (срок `session_ttl_hours`) и при `GET /embed?token=…` (срок токена витрины, 1 час). Роль `operator` даёт доступ к `/operator`; `partner_id` кабинета берётся только из сессии, не из параметров запроса.

### Встраивание
`GET /embed` отдаёт заголовок `Content-Security-Policy: frame-ancestors 'self'`. По завершении кабинет вызывает `window.parent.postMessage({type:"qod:export", payload}, window.location.origin)`; витрина слушает `message` и принимает только `event.origin === window.location.origin` и `data.type === "qod:export"`. Фолбэк — ссылка «в новой вкладке» с тем же токеном; в режиме вкладки результат показывается на странице (callback-режим).

### Трассировка 17 реплик
Помощник `trace.log(session, seq, from_, to, message)` вызывается в точках:
| seq | Где вызывается |
|---|---|
| 1–4 | `GET /qos_platform/landing` (1 на входе; 2–3 — вызов `GET /cj/qos_platform` и ответ CJ; 4 — перед ответом `200`) |
| 5–8 | `POST /qos_platform/reg` (5), `POST /cj/qos_platform` (6), `POST /px/reg` (7), ответ PX (8) |
| 9–12 | запрос `GET /rc/qos_catalog` (9), ответ (10), HTML выбора профиля (11), `200` (12) |
| 13–17 | `POST /qos_platform` (13), `POST /cj/qos_platform` (14), `POST /px/save_qos` (15), ответ (16), карточка «Партнёр подключён» (17) |
Реплики пишутся одним проходом с общим `session` (в cookie или скрытом поле формы). Эталон — V5 `flow_trace_template.json`; панель показывает по порядку `seq`.

## 11. Сид и сброс (`scripts/seed.py`, `make reset`)
Идемпотентно создаёт:
- схемы (`config/schemas`);
- `protocol` ×9;
- `qos_profile` ×5, русские названия: Бронза (10 Мбит/с, коэф. 1.0, SLA 99.0), Серебро (30, 1.5, 99.5), Золото (50, 2.0, 99.9), Платина (100, 3.0, 99.95), Бриллиант (200, 4.0, 99.99 — рабочее значение); коды `BRONZE…DIAMOND`;
- `duration` ×5 с коэффициентами 1H 0.15, 6H 0.6, 12H 1.0, 24H 1.7, 72H 4.0;
- партнёры `mts-link-1` («MTS Link») и `other-partner`;
- услуги `svc-vcs` («Link ВКС», Платина, 12H) и `svc-chat` («Link Чаты», Золото, 24H) — **обе `assignment_status = draft`** (цену подтверждает партнёр в демо); цены: 30 000 и 17 000 ₽/мес;
- сигнатуры `sig-1…sig-5` (как V4 seed, `sig-4` = `media2.mts-link.ru:5005 RTP`);
- `service_state` = `draft`.
Учётки — `config/accounts.yaml`. `make reset` удаляет `data/app.db` и запускает сид. Тест экспорта использует отдельную фикстуру (D10), где назначения `confirmed`.

## 12. Тесты (обязательные)
| Файл | Что проверяет | Источник |
|---|---|---|
| `test_schema_core.py` | 422 с полем, 404 неизвестный тип, невалидная схема не сохраняется, старые записи читаются, `x-ref`, `x-unique` | V2 A1, A7, A8 |
| `test_data_rules.py` | порт 70000, протокол SMTP, дубликат 409, каскад; кейсы `invalid_signatures.json` | V1 A1–A3, A7 |
| `test_export.py` | фикстура V1 → экспорт совпадает по структуре и значениям (кроме `generated_at`, id) с `expected_export.json` (+ наши добавленные поля); пустой партнёр → `[]`; draft-назначения не попадают | V1 A5, F7, F8 |
| `test_pricing.py` | Платина 12 ч = 30 000, Золото 12 ч = 10 000, Золото 24 ч = 17 000; смена множителя тарифа/срока или ставки в конфиге меняет цену; смена тарифа сбрасывает подтверждение | V1, V5, D15 |
| `test_auth.py` | вход верный/неверный; `/cabinet` без сессии → `/login`; сессия от токена витрины; оператор не попадает в чужой кабинет и наоборот; партнёр видит только своё | D13 |
| `test_priority.py` | `off`/`on`/`expired` по `expires_at` | D16 |
| `test_sandbox.py` | весь сценарий демо V4 и сверка журнала с `expected_event_log.json`; переходы 409; изоляция по `X-Partner-Id` | V4 A1–A9 |
| `test_mocks.py` | контракты `validate`, `qod/sessions`; `result=error` с 200 | V4 `mock_apigw_contract.json` |
| `test_token.py` | валидный/мусор/истёкший/чужая подпись | V5 A1–A3 |
| `test_trace.py` | после шагов 1–3 диаграммы в журнале 17 реплик по порядку | V5 A6 |
| `test_change_scenarios.py` | правки из `requirements.md` §5 (профиль Diamond+1, `ipv6`, `sla_percent`, `monitoring`, формула цены) без изменения кода | NFR-1 |
| `test_demo_flow.py` | e2e часть 1 `demo-script.md` через API | — |
Фикстуры — копии нужных `test_data` в `tests/fixtures/` (ссылки на `docs/source/...` в тестах не используем: путь может измениться).

## 13. Соглашения
- Код, имена, комментарии — английский; тексты UI и документация — русский.
- `ruff` (line-length 100); `make check` перед коммитом.
- Не писать код под конкретный тип сущности вне служебных таблиц (`service_state`, песочница) и мока; названия типов — только в конфиге/сидe/тестах.
- Статусы и события — только через `services`; прямых присвоений в роутах нет.
- Ошибка бизнес-правила = 409, ошибка данных = 422, нет ресурса или чужой партнёр = 404.
- Новые зависимости — только через ADR; сейчас разрешены `jsonschema`, `pyyaml`.

## 14. Порядок работ и привязка к задачам
Задачи — `docs/tasks/BOARD.md`; в каждой карточке перечислены ID требований.
| Задача | Читать в спецификации |
|---|---|
| T-001 | §3 (`relations`), §4, §5, §6 «Ядро» |
| T-002 | §3 (`protocols`), §4, §8 «Валидация», §11 |
| T-003 | §5, §7 «Рендерер форм» и `/admin/schemas` |
| T-004 | §3 (`pricing`, `px_payload`, `process`), §6 «Партнёр…», §8 «Цена» |
| T-005 | §6 «Моки» (`rc`, `px`), §7 `/px-showcase` |
| T-006 | §3 (`accounts`), §6 «Вход», §10 «Токен», «Сессия», «Встраивание» |
| T-007 | §10 «Трассировка» |
| T-008 | §4 (служебные таблицы), §8 «Автомат» |
| T-009 | §3 (`mock_rules`), §6 «Моки» (`gsma`), §9 |
| T-011 | `requirements.md` §5, §12 `test_change_scenarios.py` |
| T-012 | §11, §12 `test_demo_flow.py` |
| T-014 | §3 (`process`), §7 (`/cabinet*`), §8 «Признак приоритета», `docs/ui/02-cabinet.md` |
Критический путь: T-001 → T-002 → T-004 → T-014 → T-011; параллельно после T-002: T-003, T-004, T-005, T-008.

## 15. Что намеренно не делаем
Реальную авторизацию (CAPIF/OAuth), реальные SCEF/NEF/PCRF, CDR/биллинг, сессии CAMARA QoD (extend, события), AI-агента, два origin для витрины, миграции БД, Docker.
