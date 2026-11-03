# T-001: Конфиги, загрузчик, модели, seed

**Цель:** основа NFR-2: справочники в YAML + модели данных из `docs/domain.md`.
**Файлы:** `config/{protocols,qos_profiles,process,pricing,px_payload}.yaml`, `app/config_loader.py`, `app/models.py`, `scripts/seed.py`, `pyproject.toml` (+`pyyaml`, ADR 0003), `tests/test_config.py`, `tests/test_models.py`.
**Критерии приёмки:**
- Загрузчик читает YAML при старте и валидирует; ошибка в конфиге даёт понятное сообщение.
- Профили: ≥5 (QOS_E/S/M/L + Gold/Silver — рабочие значения, см. `analysis.md` §6), протоколы из задания.
- Модели: Partner, PartnerService, Signature, ServiceQosAssignment, Offer, SandboxRun, SandboxCheck, Subscriber, SubscriberService, NetworkRequest, AuditEvent.
- `make reset`: партнёр `partners-1` в `registered`, ≥10 абонентов.
**Вне скоупа:** движок процесса, UI.
**Зависит от:** T-000
**Журнал:**
