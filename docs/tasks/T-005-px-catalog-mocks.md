# T-005: Моки PX и каталога, карточка предложения

**Цель:** MOCK-1…MOCK-3, STD-1.
**Данные:** `v5/test_data/qos_catalog.json`, `expected_px_offer.json`.
**Файлы:** `app/mocks/px.py`, `app/mocks/resource_catalog.py`, `app/web/px_showcase.py`, `app/templates/px/*`, модель `NetworkRequest`, тесты.
**Критерии приёмки:**
- `GET /rc/qos_catalog` — профили (код, имя, Мбит/с, SLA, множитель), Duration, протоколы.
- `POST /px/reg` → `{"id":"partners-N"}`; `POST /px/save_qos` → `{"id":"qos_profiles-N"}`.
- Карточка «Партнёр подключён»: client_id, профиль, SLA из каталога, цена.
- Каждый вызов в `NetworkRequest`; поля профиля совместимы с CAMARA `QosProfile`.
**Вне скоупа:** iframe и токен.
**Зависит от:** T-002
**Журнал:**
