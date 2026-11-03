# T-005: Профили, Duration, оффер для PX

**Цель:** FR-5, FR-7, FR-8.
**Файлы:** `app/services/offer.py`, `app/api/offer.py`, `app/web/offer.py`, шаблоны, мок цены в `app/mocks/px.py`, тесты.
**Критерии приёмки:**
- Назначение профиля и Duration сервису; Duration ≤ `max_duration` профиля.
- JSON для PX собирается по маппингу `config/px_payload.yaml` и показывается в UI.
- Цена считается по `config/pricing.yaml` (мок PX); подтверждение цены → `offer_confirmed`.
**Вне скоупа:** песочница.
**Зависит от:** T-004
**Журнал:**
