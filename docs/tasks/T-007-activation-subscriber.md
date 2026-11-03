# T-007: Активация и подключение абоненту

**Цель:** FR-12, FR-13.
**Файлы:** `app/mocks/gsma_qod.py`, `app/services/activation.py`, `app/services/subscribers.py`, `app/web/subscriber.py`, шаблоны, тесты.
**Критерии приёмки:**
- Активация после успешной песочницы вызывает мок GSMA QoD APIgw (CAMARA-подобный payload: `qosProfile`, `duration`, сигнатуры), пишет `NetworkRequest`, статус `active`.
- Активный сервис подключается абоненту по MSISDN (`SubscriberService`), событие и вызов мока в журнале.
- `/subscribers/{msisdn}`: услуги, профиль, Duration, таймлайн.
**Вне скоупа:** runtime-сессии CAMARA, продление и завершение.
**Зависит от:** T-006
**Журнал:**
