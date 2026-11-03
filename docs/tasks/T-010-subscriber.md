# T-010: Подключение абоненту и карточка

**Цель:** SUB-1…SUB-3.
**Данные:** `docs/source/camara/qos-provisioning.yaml`.
**Файлы:** схемы `subscriber`, `qos_assignment`, сид абонентов, `app/mocks/qos_provisioning.py`, `app/services/subscribers.py`, `app/web/subscriber.py`, шаблоны, тесты.
**Критерии приёмки:**
- Активный (Applied) сервис подключается абоненту по номеру; запрос `POST /qos-assignments {device.phoneNumber, qosProfile}` в мок, статусы REQUESTED → AVAILABLE; запись в `NetworkRequest` и журнал.
- `/subscribers/{msisdn}`: сервисы, профиль, срок, таймлайн.
- Подключить неактивный сервис нельзя.
**Открытый вопрос:** Provisioning или QoD-сессия (analysis §7 п.4).
**Зависит от:** T-009
**Журнал:**
