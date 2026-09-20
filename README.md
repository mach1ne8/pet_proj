# Арена переговоров

Веб-симулятор переговоров для развития навыков общения. Пользователь ведёт
диалог с виртуальным оппонентом, а backend хранит историю, состояние метрик,
события evaluator и итоговый разбор сессии.

## Текущий статус

Проект находится на стадии hackathon/demo.

Уже реализовано:

- React + TypeScript + Vite frontend;
- FastAPI + SQLAlchemy Async backend;
- PostgreSQL как source of truth;
- Alembic migrations;
- сценарии переговоров;
- скрытый backend-контекст сценария для LLM;
- mock и OpenAI-compatible LLM providers;
- evaluator с Pydantic-валидацией;
- текущие метрики и история изменения метрик;
- lifecycle сессии `active -> completed`;
- итоговый результат в том же API/session flow, без отдельной Results page.

Пока по умолчанию используется deterministic mock provider. Реальный LLM endpoint
подключается настройками окружения.

## Архитектура

```text
Browser
  |
React/Vite
  |
FastAPI
  |-- PostgreSQL       история, сценарии, состояние, события, результаты
  |-- LLM provider     mock / Ollama / vLLM / OpenAI-compatible endpoint
```

Backend разделён на слои:

```text
backend/
├── api/routes/        HTTP endpoints
├── core/               config and database
├── migrations/         Alembic revisions
├── repositories/      database access
├── services/          negotiation, state and LLM logic
├── models.py           SQLAlchemy models
└── schemas.py          Pydantic API schemas
```

Скрытые цели, ограничения, BATNA и system prompt используются только внутри
backend и не возвращаются frontend.

## Требования

- Python 3.11+;
- Node.js 22+;
- npm;
- Docker Compose;
- PostgreSQL запускается только на `127.0.0.1`.

## Конфигурация

Создайте локальный `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Минимальная конфигурация:

```env
POSTGRES_PASSWORD=локальный_пароль
LLM_PROVIDER=mock
```

`.env` содержит секреты и не должен коммититься.

### LLM

Для mock режима:

```env
LLM_PROVIDER=mock
```

Для Ollama, vLLM или другого OpenAI-compatible сервиса:

```env
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_API_KEY=
LLM_MODEL=название_модели
LLM_TIMEOUT_SECONDS=60
```

LLM endpoint должен оставаться внутренним и не публиковаться напрямую в
интернет. Backend сам передаёт провайдеру приватный prompt и transcript.

## Запуск PostgreSQL

```bash
docker compose up -d postgres
docker compose ps
```

Не используйте `docker compose down -v`, если нужно сохранить данные.

## Установка и запуск backend

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r requirements.txt
```

Для новой базы:

```bash
PYTHONPATH=backend alembic upgrade head
```

Для существующей базы, созданной до появления Alembic, сначала проверьте, что
таблицы соответствуют initial schema, затем один раз выполните:

```bash
PYTHONPATH=backend alembic stamp 20260920_0001
PYTHONPATH=backend alembic upgrade head
```

`stamp` не изменяет пользовательские данные. Не выполняйте `upgrade head` на
старой немаркированной базе до этой проверки: initial migration предназначена
для пустой базы.

Запуск API:

```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
```

## Запуск frontend

```bash
npm install
npm run dev -- --host 0.0.0.0
```

Vite проксирует `/api` на `http://127.0.0.1:8000`.

## API

```text
GET  /health
GET  /api/scenarios
POST /api/sessions
GET  /api/sessions/{session_id}
POST /api/chat
POST /api/sessions/{session_id}/complete
```

Создание сессии без body использует сценарий по умолчанию. Можно передать:

```json
{
  "scenario_id": "uuid"
}
```

После каждой реплики `/api/chat` возвращает текущее состояние:

```json
{
  "message": "Ответ оппонента",
  "state": {
    "metrics": {
      "trust": 67,
      "irritation": 34,
      "interest": 78,
      "tension": 43,
      "openness": 64,
      "risk": 26
    },
    "turn_count": 1,
    "detected_tactics": ["tradeoff"],
    "coach_message": "..."
  }
}
```

После завершения статус становится `completed`, новые сообщения получают
`409`, а итог доступен через тот же `GET /api/sessions/{session_id}`.

## Проверки

```bash
PYTHONPATH=backend alembic current
PYTHONPATH=backend alembic check
find backend -path 'backend/.venv' -prune -o -name '*.py' -print0 \
  | xargs -0 python3 -m py_compile
npm run build
```

## Безопасность

- секреты хранятся только в `.env`;
- PostgreSQL, Redis и LLM endpoint не должны быть доступны из интернета;
- frontend не получает hidden prompts;
- пользовательские сообщения ограничены по длине и валидируются Pydantic;
- доступ к сессиям пользователя потребует ownership checks после добавления
  авторизации;
- production deployment должен использовать Nginx перед frontend/backend.
