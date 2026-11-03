# QoS-платформа — прототип управления сервисами партнёра (хакатон МТС 2026)

Прототип шагов 3–8 процесса: партнёр описывает сервисы и сигнатуры, назначает QoS-профили и Duration,
получает цену от PX, проходит песочницу и активирует сервис (эмуляция GSMA QoD APIgw); затем сервис
подключается конкретному абоненту. Суть задания — **минимальная стоимость и скорость изменений**.

## Запуск
```bash
uv sync
make reset   # создать БД с демо-данными
make dev     # http://localhost:8000 , Swagger: /docs
make check   # линтер + тесты
```

## Документация
- Первоисточники: [docs/source/](docs/source/README.md)
- Требования: [docs/requirements.md](docs/requirements.md) · Разбор: [docs/analysis.md](docs/analysis.md) · Глоссарий: [docs/glossary.md](docs/glossary.md)
- Модель и процесс: [docs/domain.md](docs/domain.md) · Архитектура: [docs/architecture.md](docs/architecture.md)
- Сценарий демо: [docs/demo-script.md](docs/demo-script.md)

## Для разработчиков и агентов
Правила — [AGENTS.md](AGENTS.md). Задачи — [docs/tasks/BOARD.md](docs/tasks/BOARD.md).
Разработка идёт итерациями разными агентами (Claude Code, Codex, Cursor).
