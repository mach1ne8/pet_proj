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
- итоговый результат в том же API/session flow, без отдельной Results page;
- выбор длительности раунда от 10 до 60 минут с серверным дедлайном;
- ответвление диалога от выбранной реплики игрока без удаления исходной сессии;
- уровни с разной видимостью метрик, SOS и генерация быстрых реплик через LLM;
- браузерный демо-кабинет с историей раундов, заметками и диаграммой навыков;
- асинхронный анализ навыков по завершённым раундам и экспорт отчёта в PDF;
- LLM-выжимка завершённого диалога с резервным разбором на случай недоступности модели;
- быстрый переход к итогам: LLM-выжимка дополняет сохранённый результат в фоне;
- три разные SOS-подсказки с сохранением истории в PostgreSQL;
- пять достижений, начисляемых по итогам раунда и видимых в демо-кабинете.

Демо-кабинет показывает раунды, созданные после введения новой системы оценки.
Старые тестовые сессии остаются в PostgreSQL, но не входят в статистику кабинета.

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

Скрытые цели, ограничения и system prompt используются только внутри backend.
BATNA возвращается frontend только после вопроса игрока об альтернативах.

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

Для публичного запуска используйте сборку frontend и Nginx вместо Vite dev
server. Конфигурация, лимиты запросов и варианты защиты ВМ описаны в
[deploy/README.md](deploy/README.md).

## API

```text
GET  /health
GET  /api/scenarios
POST /api/sessions
GET  /api/sessions/{session_id}
POST /api/chat
POST /api/sessions/{session_id}/complete
POST /api/sessions/{session_id}/fork
PATCH /api/sessions/{session_id}/notes
POST /api/sessions/{session_id}/hint
POST /api/sessions/{session_id}/suggest
POST /api/profile-reports
GET  /api/profile-reports/{report_id}
```

На стартовом экране доступны «Закупки с поставщиком», «Повышение зарплаты»
и «Сроки проекта с клиентом». Выбранный сценарий определяет роль оппонента,
стартовую реплику и скрытый контекст LLM; сложность выбирается отдельно.

Создание сессии без body использует сценарий по умолчанию. Можно передать:

```json
{
  "scenario_id": "uuid",
  "difficulty": "beginner"
}
```

Уровни `beginner`, `analyst`, `advanced`, `expert` управляют видимостью метрик:
новичок видит состояние собеседника (раздражение, напряжение, открытость) и
ход переговоров (доверие, интерес, риск срыва); аналитик — только ход
переговоров; переговорщик и мастер не видят чисел во время диалога. Полные
метрики доступны после завершения. После каждой
реплики `/api/chat` возвращает разрешённое для текущего уровня состояние:

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
    "coach_message": "",
    "signal": null
  }
}
```

Стартовые метрики новых раундов тоже различаются: новичок начинает с более
благоприятной позиции, аналитик — с осторожной, переговорщик и мастер — с
более напряжённой. Итоговый балл учитывает изменения относительно стартового
снимка именно этого раунда, а не общей константы сценария.

После завершения статус становится `completed`, новые сообщения получают
`409`, а итог доступен через тот же `GET /api/sessions/{session_id}`. Сессии с
нулём реплик получают `0/100`. SOS доступен на уровнях новичка и аналитика,
не более трёх раз за раунд; каждая подсказка снижает итог на 8 баллов.
История подсказок возвращается в `hint_history`. Результат сразу доступен с
`analysis_status: "pending"`; когда фоновый LLM-разбор завершён, статус становится
`ready`. При ошибке остаётся сохранённый базовый разбор и статус `failed`.
Фоновая задача пока выполняется в процессе FastAPI: если он перезапустится до
завершения, следующий `GET` сессии повторно запустит анализ со статусом
`pending`. Для production потребуется отдельный устойчивый worker.
`suggest` принимает `tactic` (`open_question`, `interests`, `facts`,
`compromise`) и возвращает подготовленную реплику для редактирования на
уровнях новичка и аналитика. Переговорщик не видит чисел и не получает SOS
или готовые фразы, но после своего хода получает один качественный `signal`,
выведенный из сохранённых изменений метрик. Мастер не получает ни сигналов,
ни списка распознанных техник до завершения раунда; чат занимает больше места.
Заметки и возврат к своим ходам доступны на всех уровнях.

`result.achievements` хранит идентификаторы достижений. Они начисляются только
при завершении нового содержательного раунда: за первый диалог, вопросы в трёх
ходах, раскрытие BATNA, три хода без SOS, рост доверия на 10 пунктов при
снижении риска срыва на 5. В кабинете одинаковые достижения разных раундов
объединяются; старые тестовые результаты не пересчитываются.
В итогах отображаются только достижения текущего раунда, а в кабинете — весь
каталог с открытыми и закрытыми достижениями.

Для отката `POST /api/sessions/{session_id}/fork` принимает
`{"turn_count": 2, "notes": "..."}`: создаётся новая ветка **перед** второй
репликой игрока. Исходная сессия и её история сохраняются; у новой ветки
тот же дедлайн и уже использованные SOS, но состояние и сообщения
восстанавливаются из сохранённого снимка перед выбранным ходом.

Кабинет `/profile` пока привязан к списку UUID, сохранённому в этом браузере.
Заметки и результаты хранятся в PostgreSQL; полноценная синхронизация между
устройствами появится после авторизации и проверки владельца сессии.
Кнопка «Разобрать мои навыки» создаёт отчёт по максимум 20 завершённым раундам;
результат сохраняется и доступен по ссылке `/profile/analysis/{report_id}`.
Кнопка «Экспорт в PDF» открывает диалог печати браузера, где нужно выбрать
«Сохранить как PDF». Пока нет авторизации, ссылку на отчёт не следует передавать
другим: любой, кто узнает UUID отчёта, сможет его открыть.

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
