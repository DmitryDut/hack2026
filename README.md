# QoS-платформа — прототип управления сервисами партнёра (хакатон МТС 2026)

Прототип шагов 3–8 процесса: партнёр описывает сервисы и сигнатуры, назначает QoS-профили и Duration,
получает цену от PX, проходит песочницу и активирует сервис (эмуляция GSMA QoD APIgw); затем сервис
включается в сети. Суть задания — **минимальная стоимость и скорость изменений**.

## Запуск
```bash
uv sync
make demo    # сбросить БД, загрузить демо-данные и запустить на http://localhost:8000
make check   # линтер + 46 тестов
make progress   # прогресс по docs/PLAN.md;  make todo — отложенное
```
Вход: партнёр `mts-link-1` / `demo`, оператор `operator` / `demo` (правки справочников и схем). Витрина PX: `/px-showcase`; флоу из диаграммы задания: `/qos_platform/landing`.

## Документация
- Первоисточники, варианты ТЗ и тестовые данные: [docs/source/](docs/source/README.md)
- Требования (ФТ/НФТ): [docs/requirements.md](docs/requirements.md) · Разбор: [docs/analysis.md](docs/analysis.md) · Глоссарий: [docs/glossary.md](docs/glossary.md)
- **Спецификация реализации:** [docs/SPEC.md](docs/SPEC.md) · **Передача работы другому агенту:** [docs/HANDOFF.md](docs/HANDOFF.md)
- Модель и процесс: [docs/domain.md](docs/domain.md) · Архитектура: [docs/architecture.md](docs/architecture.md)
- **План, шаги и TODO:** [docs/PLAN.md](docs/PLAN.md) · **Правки «поменяйте вот это»:** [docs/change-playbook.md](docs/change-playbook.md)
- Макеты интерфейсов (черновик): [docs/ui/](docs/ui/README.md) · Реализуемые сценарии: [docs/scenarios.md](docs/scenarios.md)
- Сценарий демо: [docs/demo-script.md](docs/demo-script.md)

## Для разработчиков и агентов
Правила — [AGENTS.md](AGENTS.md). Задачи — [docs/tasks/BOARD.md](docs/tasks/BOARD.md).
Разработка идёт итерациями разными агентами (Claude Code, Codex, Cursor).
