# T-003: Моки PX и Resource Catalog, лендинг, embed

**Цель:** шаги 1–2 flow-диаграммы задания в виде моков + вход партнёра в платформу.
**Файлы:** `app/mocks/px.py`, `app/mocks/resource_catalog.py`, `app/web/landing.py`, `app/templates/landing/*`, режим `?embed=1` в `base.html`.
**Критерии приёмки:**
- `GET /rc/qos_catalog` отдаёт профили из конфига; `POST /px/reg` возвращает `{"id": "partners-N"}`.
- `/qos_platform/landing?partner_id=...` открывает кабинет партнёра; `?embed=1` скрывает шапку.
- Вызовы моков пишутся в `NetworkRequest`.
**Вне скоупа:** сервисы и сигнатуры.
**Зависит от:** T-002
**Журнал:**
