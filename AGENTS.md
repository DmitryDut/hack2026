# AGENTS.md — общие правила для всех агентов (Claude Code, Codex, Cursor)

## Проект
POC для хакатона МТС: QoS-платформа (QoD management). Партнёр уже прошёл регистрацию/контракт в PX;
мы делаем шаги 3–8: сервисы и сигнатуры `{IPv4, URI, port, protocol}` → QoS-профили и Duration →
JSON в PX, подтверждение цены → песочница → активация (эмуляция GSMA QoD APIgw) → подключение
сервиса абоненту (MSISDN). **Главный критерий — дешевизна и скорость изменений:** процесс, модель,
API и UI должны меняться без полного цикла разработки (ADR 0003).
Внешние системы (PX, каталог, GSMA APIgw) — встроенные моки с журналом (ADR 0002).
Финал запускается локально на одной машине — не усложняй.

Читай перед работой: `docs/requirements.md` (требования FR/NFR), `docs/analysis.md` (разбор и допущения),
`docs/glossary.md`, `docs/domain.md`, `docs/architecture.md`, `docs/demo-script.md`,
`docs/tasks/README.md` (протокол задач). Первоисточники — `docs/source/` (не редактировать).

## Стек и команды
Python 3.12+, FastAPI, SQLModel + SQLite, Jinja2 + HTMX + Pico.css (CDN). Менеджер: `uv`.
- `make dev` — запуск на http://localhost:8000 (Swagger: `/docs`)
- `make test` / `make lint` / `make fmt` / `make check` (lint + test)
- `make seed` / `make reset` — демо-данные / пересоздать БД

## Архитектура и правила кода
- Слои: `app/web` и `app/api` (тонкие роуты) → `app/services` (вся бизнес-логика) → `app/models.py`.
- Смена статуса сущности — ТОЛЬКО через функцию сервиса, которая проверяет допустимость перехода
  и пишет `AuditEvent`. Прямых присвоений `.status = ...` в роутах нет.
- Код, имена, комментарии — на английском; тексты UI и документация — на русском.
- Справочники, процесс, правила цены и шаблон JSON для PX меняются в `config/*.yaml`, не в коде.
- Без миграций: схема создаётся `create_all`, при изменении моделей — `make reset`.
- Новые зависимости, инфраструктура (Docker, очереди, Node-сборка) — только через ADR в `docs/decisions/`.

## Работа с задачами (кратко; полно — `docs/tasks/README.md`)
1. `git pull`, возьми задачу `todo` из `docs/tasks/BOARD.md`, поставь `in_progress` + своё имя
   (`claude` / `codex` / `cursor`), создай ветку `t-XXX-short-name` (лучше в отдельном git worktree).
2. Делай ТОЛЬКО то, что в карточке `docs/tasks/T-XXX-*.md`; общие файлы (`models.py`, `main.py`,
   `seed.py`) трогай, только если это указано в карточке.
3. В конце допиши в карточку «Журнал» (что сделано, что осталось) — следующий агент может быть другим.
4. Коммит `T-XXX: описание` → `git pull --rebase origin main` → merge в `main` → `git push`.

## Definition of Done
- `make check` зелёный; для новой логики есть тест.
- Обновлены `docs/domain.md` / `docs/demo-script.md`, если изменилось поведение.
- Статус в `BOARD.md` = `done`, журнал в карточке заполнен.
- В репо нет секретов и файлов из `data/` (репозиторий публичный).
