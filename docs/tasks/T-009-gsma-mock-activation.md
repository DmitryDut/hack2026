# T-009: Мок GSMA APIgw, активация, изоляция

**Цель:** SBX-7, SBX-9, SBX-10, STD-2, STD-3.
**Данные:** `v4/test_data/mock_apigw_contract.json`, `demo_scenario.json`; `docs/source/zadanie/TS29122_*.yaml`, `docs/source/camara/*`.
**Файлы:** `app/mocks/gsma_qod.py`, `app/services/activation.py`, фильтр по `X-Partner-Id`, тесты.
**Критерии приёмки:**
- `POST /mock-gsma/validate` детерминирован (`media2:5005` — error, 5006 — success), `result=error` приходит с HTTP 200, задержка 300–800 мс.
- `POST /mock-gsma/qod/sessions` из Passed → `session_id`, статус Applied; payload отражает CAMARA (`applicationServer`, порты, `duration` в секундах) и 3GPP (`flowInfo`, `qosDuration`), URI/protocol → PFD-блок.
- Чужой `X-Partner-Id` не видит сервисы партнёра (V4 A6, A9).
- Вызовы в `NetworkRequest`.
**Зависит от:** T-008
**Журнал:**
