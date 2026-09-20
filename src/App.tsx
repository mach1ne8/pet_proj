import { useEffect, useRef, useState } from 'react'
import './index.css'

const SESSION_STORAGE_KEY = 'negotiation_session_id'

type MetricProps = {
  title: string
  value: number
  variant?: 'blue' | 'green' | 'orange'
}

type ChatMessage = {
  id: number
  author: 'Собеседник' | 'Вы'
  text: string
  time: string
  mine: boolean
}

type ApiMessage = {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

type SessionResponse = {
  session_id: string
  messages: ApiMessage[]
}

type ChatResponse = {
  message: string
}

function Metric({
  title,
  value,
  variant = 'blue',
}: MetricProps) {
  return (
    <div className="metric">
      <div className="metric-header">
        <span>{title}</span>
        <span>{value}%</span>
      </div>

      <div className="metric-track">
        <div
          className={`metric-fill ${variant}`}
          style={{
            width: `${value}%`,
          }}
        />
      </div>
    </div>
  )
}

function Message({
  author,
  text,
  time,
  mine,
}: {
  author: string
  text: string
  time: string
  mine: boolean
}) {
  return (
    <div className={`message-row ${mine ? 'mine' : ''}`}>
      <div className="avatar">
        {mine ? 'В' : 'С'}
      </div>

      <div className={`message ${mine ? 'message-mine' : ''}`}>
        <div className="message-meta">
          <strong>{author}</strong>
          <span>{time}</span>
        </div>

        <div className="message-text">
          {text}
        </div>
      </div>
    </div>
  )
}

function getCurrentTime() {
  return new Date().toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatApiTime(createdAt: string) {
  return new Date(createdAt).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function mapApiMessages(
  apiMessages: ApiMessage[],
): ChatMessage[] {
  return apiMessages.map((apiMessage, index) => ({
    id: index + 1,

    author:
      apiMessage.role === 'user'
        ? 'Вы'
        : 'Собеседник',

    text: apiMessage.content,

    time: formatApiTime(
      apiMessage.created_at,
    ),

    mine: apiMessage.role === 'user',
  }))
}

function App() {
  const [message, setMessage] = useState('')

  const [sessionId, setSessionId] =
    useState<string | null>(null)

  const [messages, setMessages] =
    useState<ChatMessage[]>([])

  const [isOpponentThinking, setIsOpponentThinking] =
    useState(false)

  const [sessionError, setSessionError] =
    useState<string | null>(null)

  const [isSessionLoading, setIsSessionLoading] =
    useState(true)

  const messagesEndRef =
    useRef<HTMLDivElement | null>(null)

  const sessionStartedRef =
    useRef(false)

  /*
   * Создание новой переговорной сессии.
   */
  const createSession = async () => {
    const response = await fetch('/api/sessions', {
      method: 'POST',
    })

    if (!response.ok) {
      throw new Error(
        `Ошибка создания сессии: HTTP ${response.status}`,
      )
    }

    const data: SessionResponse =
      await response.json()

    /*
     * Сохраняем session_id в браузере.
     */
    localStorage.setItem(
      SESSION_STORAGE_KEY,
      data.session_id,
    )

    setSessionId(data.session_id)

    setMessages(
      mapApiMessages(data.messages),
    )
  }

  /*
   * Восстановление существующей сессии.
   */
  const restoreSession = async (
    storedSessionId: string,
  ) => {
    const response = await fetch(
      `/api/sessions/${storedSessionId}`,
    )

    /*
     * Например, FastAPI был перезапущен,
     * sessions = {} очистился,
     * а браузер всё ещё хранит старый UUID.
     */
    if (response.status === 404) {
      localStorage.removeItem(
        SESSION_STORAGE_KEY,
      )

      await createSession()

      return
    }

    if (!response.ok) {
      throw new Error(
        `Ошибка восстановления сессии: HTTP ${response.status}`,
      )
    }

    const data: SessionResponse =
      await response.json()

    setSessionId(data.session_id)

    setMessages(
      mapApiMessages(data.messages),
    )
  }

  /*
   * При открытии страницы:
   *
   * 1. Ищем session_id в localStorage.
   * 2. Если есть -> восстанавливаем историю.
   * 3. Если нет -> создаём новую сессию.
   */
  useEffect(() => {
    if (sessionStartedRef.current) {
      return
    }

    sessionStartedRef.current = true

    const initializeSession = async () => {
      try {
        setIsSessionLoading(true)
        setSessionError(null)

        const storedSessionId =
          localStorage.getItem(
            SESSION_STORAGE_KEY,
          )

        if (storedSessionId) {
          await restoreSession(
            storedSessionId,
          )
        } else {
          await createSession()
        }
      } catch (error) {
        console.error(
          'Ошибка инициализации сессии:',
          error,
        )

        setSessionError(
          'Не удалось загрузить переговорную сессию',
        )
      } finally {
        setIsSessionLoading(false)
      }
    }

    initializeSession()
  }, [])

  /*
   * Автоматическая прокрутка чата вниз.
   */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
    })
  }, [messages, isOpponentThinking])

  /*
   * Отправка сообщения.
   */
  const sendMessage = async () => {
    const text = message.trim()

    if (
      !text ||
      !sessionId ||
      isOpponentThinking
    ) {
      return
    }

    const userMessage: ChatMessage = {
      id: Date.now(),
      author: 'Вы',
      text,
      time: getCurrentTime(),
      mine: true,
    }

    setMessages((prev) => [
      ...prev,
      userMessage,
    ])

    setMessage('')
    setIsOpponentThinking(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',

        headers: {
          'Content-Type': 'application/json',
        },

        body: JSON.stringify({
          session_id: sessionId,
          message: text,
        }),
      })

      /*
       * Если сессия исчезла на backend,
       * например после рестарта FastAPI.
       */
      if (response.status === 404) {
        localStorage.removeItem(
          SESSION_STORAGE_KEY,
        )

        throw new Error(
          'Переговорная сессия больше не существует',
        )
      }

      if (!response.ok) {
        throw new Error(
          `Ошибка API: HTTP ${response.status}`,
        )
      }

      const data: ChatResponse =
        await response.json()

      const opponentMessage: ChatMessage = {
        id: Date.now() + 1,
        author: 'Собеседник',
        text: data.message,
        time: getCurrentTime(),
        mine: false,
      }

      setMessages((prev) => [
        ...prev,
        opponentMessage,
      ])
    } catch (error) {
      console.error(
        'Ошибка отправки сообщения:',
        error,
      )
    } finally {
      setIsOpponentThinking(false)
    }
  }

  return (
    <div className="app">

      {/* HEADER */}

      <header className="topbar">
        <div className="brand">
          <div className="brand-logo">
            A
          </div>

          <div>
            <div className="brand-title">
              Арена переговоров
            </div>

            <div className="brand-subtitle">
              Симулятор развития навыков переговоров
            </div>
          </div>
        </div>

        <div className="level">
          <div className="level-text">
            <strong>
              Уровень:
            </strong>{' '}
            Аналитик
          </div>

          <div className="level-track">
            <div className="level-progress" />
          </div>
        </div>

        <div className="timer">
          <span className="timer-label">
            Время
          </span>

          <strong>
            08:14
          </strong>
        </div>
      </header>

      <main className="arena-layout">

        {/* LEFT PANEL */}

        <aside className="panel side-panel">
          <div className="panel-title">
            Эмоциональный барометр
          </div>

          <div className="panel-subtitle">
            Состояние собеседника
          </div>

          <div className="metrics">
            <Metric
              title="Раздражение"
              value={35}
              variant="orange"
            />

            <Metric
              title="Интерес"
              value={78}
              variant="green"
            />

            <Metric
              title="Напряжение"
              value={42}
            />

            <Metric
              title="Открытость"
              value={64}
              variant="green"
            />
          </div>

          <div className="hidden-goal">
            <div className="hidden-goal-title">
              Скрытая цель
            </div>

            <div className="hidden-goal-value">
              🔒 Неизвестно
            </div>
          </div>
        </aside>

        {/* CHAT */}

        <section className="chat-panel">

          <div className="chat-header">
            <div>
              <div className="panel-title">
                Арена переговоров
              </div>

              <div className="panel-subtitle">
                Закупки с поставщиком
              </div>
            </div>

            <span className="status-badge">
              Переговоры идут
            </span>
          </div>

          <div className="progress-dots">
            <span className="dot active" />
            <span className="dot active" />
            <span className="dot active" />
            <span className="dot active" />
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>

          <div className="messages">

            {sessionError && (
              <div className="message-row">
                <div className="avatar">
                  !
                </div>

                <div className="message">
                  <div className="message-text">
                    {sessionError}
                  </div>
                </div>
              </div>
            )}

            {isSessionLoading && (
              <div className="message-row">
                <div className="avatar">
                  С
                </div>

                <div className="message">
                  <div className="message-text">
                    Загрузка переговорной сессии...
                  </div>
                </div>
              </div>
            )}

            {!isSessionLoading &&
              messages.map((msg) => (
                <Message
                  key={msg.id}
                  author={msg.author}
                  text={msg.text}
                  time={msg.time}
                  mine={msg.mine}
                />
              ))}

            {isOpponentThinking && (
              <div className="message-row">
                <div className="avatar">
                  С
                </div>

                <div className="message">
                  <div className="message-meta">
                    <strong>
                      Собеседник
                    </strong>
                  </div>

                  <div className="message-text">
                    Печатает...
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* QUICK ACTIONS */}

          <div className="quick-actions">
            <button>
              Задать открытый вопрос
            </button>

            <button>
              Сделать комплимент
            </button>

            <button>
              Указать на факт
            </button>

            <button>
              Предложить компромисс
            </button>
          </div>

          {/* INPUT */}

          <div className="message-input">
            <textarea
              placeholder={
                sessionId
                  ? 'Введите вашу реплику...'
                  : 'Загрузка сессии...'
              }
              value={message}
              disabled={
                isOpponentThinking ||
                isSessionLoading ||
                !sessionId
              }
              onChange={(event) => {
                setMessage(
                  event.target.value,
                )
              }}
              onKeyDown={(event) => {
                if (
                  event.key === 'Enter' &&
                  !event.shiftKey
                ) {
                  event.preventDefault()
                  sendMessage()
                }
              }}
            />

            <button
              onClick={sendMessage}
              disabled={
                isOpponentThinking ||
                isSessionLoading ||
                !sessionId
              }
            >
              ➜
            </button>
          </div>

        </section>

        {/* RIGHT PANEL */}

        <aside className="panel side-panel">
          <div className="panel-title">
            Панель метрик
          </div>

          <div className="panel-subtitle">
            Ваш результат
          </div>

          <div className="metrics">

            <Metric
              title="Выгода"
              value={72}
              variant="green"
            />

            <Metric
              title="Отношения"
              value={81}
              variant="green"
            />

            <Metric
              title="Время"
              value={67}
            />

            <Metric
              title="Риск срыва"
              value={28}
              variant="orange"
            />

            <Metric
              title="Репутация"
              value={86}
              variant="green"
            />

            <Metric
              title="Доверие"
              value={65}
            />

          </div>

          <div className="coach-card">
            <div className="coach-title">
              AI-коуч
            </div>

            <p>
              Собеседник проявляет интерес к
              долгосрочному сотрудничеству.
              Попробуйте выяснить его реальные
              ограничения.
            </p>
          </div>
        </aside>

      </main>
    </div>
  )
}

export default App
