import { useEffect, useMemo, useRef, useState } from 'react'
import './index.css'

const SESSION_STORAGE_KEY = 'negotiation_session_id'
const DIFFICULTY_STORAGE_KEY = 'negotiation_difficulty'
const NOTES_STORAGE_PREFIX = 'negotiation_notes_'
const SESSION_STARTED_PREFIX = 'negotiation_started_at_'

type View = 'setup' | 'active' | 'completed'
type Difficulty = 'beginner' | 'analyst' | 'advanced' | 'expert'

type MetricProps = {
  title: string
  value: number
  variant?: 'blue' | 'green' | 'orange'
  compact?: boolean
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

type SessionState = {
  metrics: Record<string, number>
  turn_count: number
  detected_tactics: string[]
  coach_message: string
}

type SessionResult = {
  final_score: number
  outcome: string
  final_metrics: Record<string, number>
  strengths: string[]
  mistakes: string[]
  recommendations: string[]
  completed_at: string
}

type SessionResponse = {
  session_id: string
  status: 'active' | 'completed' | 'abandoned'
  scenario_id: string | null
  state: SessionState | null
  result: SessionResult | null
  messages: ApiMessage[]
}

type ChatResponse = {
  message: string
  state: SessionState
}

type Scenario = {
  id: string
  slug: string
  name: string
  description: string
  character_name: string
  character_role: string
  difficulty: string
}

const difficultyOptions: Array<{
  id: Difficulty
  label: string
  description: string
  metricMode: 'full' | 'focused' | 'hidden'
}> = [
  {
    id: 'beginner',
    label: 'Новичок',
    description: 'Все ключевые сигналы видны во время диалога.',
    metricMode: 'full',
  },
  {
    id: 'analyst',
    label: 'Аналитик',
    description: 'Показываем только самые важные изменения состояния.',
    metricMode: 'focused',
  },
  {
    id: 'advanced',
    label: 'Переговорщик',
    description: 'Live-метрики скрыты, подсказки появятся после раунда.',
    metricMode: 'hidden',
  },
  {
    id: 'expert',
    label: 'Мастер',
    description: 'Максимально реалистичный режим без live-оценки.',
    metricMode: 'hidden',
  },
]

const tacticLabels: Record<string, string> = {
  open_question: 'Открытый вопрос',
  empathy: 'Эмпатия',
  position_statement: 'Позиция',
  fact_based_argument: 'Аргументация фактами',
  concession: 'Уступка',
  compromise: 'Компромисс',
}

function getStoredDifficulty(): Difficulty {
  const storedDifficulty = localStorage.getItem(DIFFICULTY_STORAGE_KEY) as Difficulty | null
  return storedDifficulty && difficultyOptions.some((item) => item.id === storedDifficulty)
    ? storedDifficulty
    : 'analyst'
}

function Metric({
  title,
  value,
  variant = 'blue',
  compact = false,
}: MetricProps) {
  const safeValue = Math.max(0, Math.min(100, value))

  return (
    <div className={`metric ${compact ? 'metric-compact' : ''}`}>
      <div className="metric-header">
        <span>{title}</span>
        <span>{safeValue}%</span>
      </div>
      <div className="metric-track">
        <div
          className={`metric-fill ${variant}`}
          style={{ width: `${safeValue}%` }}
        />
      </div>
    </div>
  )
}

function ArrowIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="button-arrow">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
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
      <div className="avatar">{mine ? 'В' : 'С'}</div>
      <div className={`message ${mine ? 'message-mine' : ''}`}>
        <div className="message-meta">
          <strong>{author}</strong>
          <span>{time}</span>
        </div>
        <div className="message-text">{text}</div>
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

function mapApiMessages(apiMessages: ApiMessage[]): ChatMessage[] {
  return apiMessages.map((apiMessage, index) => ({
    id: index + 1,
    author: apiMessage.role === 'user' ? 'Вы' : 'Собеседник',
    text: apiMessage.content,
    time: formatApiTime(apiMessage.created_at),
    mine: apiMessage.role === 'user',
  }))
}

function formatDuration(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function App() {
  const [view, setView] = useState<View>('setup')
  const [difficulty, setDifficulty] = useState<Difficulty>(getStoredDifficulty)
  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [state, setState] = useState<SessionState | null>(null)
  const [result, setResult] = useState<SessionResult | null>(null)
  const [message, setMessage] = useState('')
  const [notes, setNotes] = useState('')
  const [isNotesOpen, setIsNotesOpen] = useState(false)
  const [isTranscriptOpen, setIsTranscriptOpen] = useState(false)
  const [isOpponentThinking, setIsOpponentThinking] = useState(false)
  const [isSessionLoading, setIsSessionLoading] = useState(true)
  const [isStarting, setIsStarting] = useState(false)
  const [isCompleting, setIsCompleting] = useState(false)
  const [sessionError, setSessionError] = useState<string | null>(null)
  const [startedAt, setStartedAt] = useState<number | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const sessionStartedRef = useRef(false)

  const selectedDifficulty = useMemo(
    () => difficultyOptions.find((item) => item.id === difficulty)!,
    [difficulty],
  )

  const metrics = state?.metrics ?? {}
  const activeMetrics = selectedDifficulty.metricMode === 'full'
    ? [
        { title: 'Доверие', key: 'trust', variant: 'blue' as const },
        { title: 'Интерес', key: 'interest', variant: 'green' as const },
        { title: 'Открытость', key: 'openness', variant: 'green' as const },
        { title: 'Риск срыва', key: 'risk', variant: 'orange' as const },
      ]
    : [
        { title: 'Доверие', key: 'trust', variant: 'blue' as const },
        { title: 'Риск срыва', key: 'risk', variant: 'orange' as const },
      ]

  const saveNotes = (value: string) => {
    setNotes(value)
    if (sessionId) {
      localStorage.setItem(`${NOTES_STORAGE_PREFIX}${sessionId}`, value)
    }
  }

  const applySession = (data: SessionResponse) => {
    setSessionId(data.session_id)
    setMessages(mapApiMessages(data.messages))
    setState(data.state)
    setResult(data.result)
    setScenario((current) => (
      current ?? scenarios.find((item) => item.id === data.scenario_id) ?? null
    ))
    const storedNotes = localStorage.getItem(`${NOTES_STORAGE_PREFIX}${data.session_id}`)
    setNotes(storedNotes ?? '')
    if (data.status === 'completed') {
      const savedStartedAt = localStorage.getItem(`${SESSION_STARTED_PREFIX}${data.session_id}`)
      if (savedStartedAt && data.result) {
        setElapsedSeconds(Math.max(0, Math.floor((new Date(data.result.completed_at).getTime() - Number(savedStartedAt)) / 1000)))
      }
      setView('completed')
    } else if (data.status === 'active') {
      setView('active')
      const savedStartedAt = localStorage.getItem(`${SESSION_STARTED_PREFIX}${data.session_id}`)
      const sessionStartedAt = savedStartedAt ? Number(savedStartedAt) : Date.now()
      setStartedAt(sessionStartedAt)
      if (!savedStartedAt) {
        localStorage.setItem(`${SESSION_STARTED_PREFIX}${data.session_id}`, String(sessionStartedAt))
      }
    }
  }

  const fetchScenarios = async () => {
    const response = await fetch('/api/scenarios')
    if (!response.ok) throw new Error(`Ошибка загрузки сценариев: HTTP ${response.status}`)
    const data: Scenario[] = await response.json()
    setScenarios(data)
    setScenario((current) => current ?? data[0] ?? null)
  }

  const createSession = async (scenarioId?: string) => {
    const response = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(scenarioId ? { scenario_id: scenarioId } : {}),
    })
    if (!response.ok) throw new Error(`Ошибка создания сессии: HTTP ${response.status}`)
    const data: SessionResponse = await response.json()
    localStorage.setItem(SESSION_STORAGE_KEY, data.session_id)
    const sessionStartedAt = Date.now()
    localStorage.setItem(`${SESSION_STARTED_PREFIX}${data.session_id}`, String(sessionStartedAt))
    applySession(data)
    setView('active')
    setStartedAt(sessionStartedAt)
  }

  const restoreSession = async (storedSessionId: string) => {
    const response = await fetch(`/api/sessions/${storedSessionId}`)
    if (response.status === 404) {
      localStorage.removeItem(SESSION_STORAGE_KEY)
      return
    }
    if (!response.ok) throw new Error(`Ошибка восстановления сессии: HTTP ${response.status}`)
    const data: SessionResponse = await response.json()
    applySession(data)
  }

  useEffect(() => {
    if (sessionStartedRef.current) return
    sessionStartedRef.current = true

    const initialize = async () => {
      try {
        setIsSessionLoading(true)
        await fetchScenarios()
        const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)
        if (storedSessionId) await restoreSession(storedSessionId)
      } catch (error) {
        console.error('Ошибка инициализации:', error)
        setSessionError('Не удалось загрузить сценарии и переговорную сессию')
      } finally {
        setIsSessionLoading(false)
      }
    }
    void initialize()
    // Initialization is intentionally guarded by the ref above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!startedAt || view !== 'active') return
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [startedAt, view])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isOpponentThinking])

  const startNegotiation = async () => {
    if (!scenario || isStarting) return
    try {
      setIsStarting(true)
      setSessionError(null)
      localStorage.setItem(DIFFICULTY_STORAGE_KEY, difficulty)
      localStorage.removeItem(SESSION_STORAGE_KEY)
      await createSession(scenario.id)
    } catch (error) {
      console.error('Ошибка старта:', error)
      setSessionError('Не удалось начать переговоры')
    } finally {
      setIsStarting(false)
    }
  }

  const sendMessage = async () => {
    const text = message.trim()
    if (!text || !sessionId || isOpponentThinking || view !== 'active') return

    const userMessage: ChatMessage = {
      id: Date.now(),
      author: 'Вы',
      text,
      time: getCurrentTime(),
      mine: true,
    }
    setMessages((prev) => [...prev, userMessage])
    setMessage('')
    setIsOpponentThinking(true)
    setSessionError(null)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      })
      if (response.status === 404) {
        localStorage.removeItem(SESSION_STORAGE_KEY)
        throw new Error('Переговорная сессия больше не существует')
      }
      if (!response.ok) throw new Error(`Ошибка API: HTTP ${response.status}`)

      const data: ChatResponse = await response.json()
      setState(data.state)
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          author: 'Собеседник',
          text: data.message,
          time: getCurrentTime(),
          mine: false,
        },
      ])
    } catch (error) {
      console.error('Ошибка отправки сообщения:', error)
      setSessionError('Не удалось получить ответ. Попробуйте ещё раз.')
    } finally {
      setIsOpponentThinking(false)
    }
  }

  const completeSession = async () => {
    if (!sessionId || isCompleting || isOpponentThinking) return
    try {
      setIsCompleting(true)
      const response = await fetch(`/api/sessions/${sessionId}/complete`, { method: 'POST' })
      if (!response.ok) throw new Error(`Ошибка завершения: HTTP ${response.status}`)
      const data: SessionResponse = await response.json()
      applySession(data)
      setView('completed')
    } catch (error) {
      console.error('Ошибка завершения:', error)
      setSessionError('Не удалось завершить переговоры')
    } finally {
      setIsCompleting(false)
    }
  }

  const startNewSession = () => {
    localStorage.removeItem(SESSION_STORAGE_KEY)
    setSessionId(null)
    setMessages([])
    setState(null)
    setResult(null)
    setNotes('')
    setMessage('')
    setSessionError(null)
    setIsTranscriptOpen(false)
    setView('setup')
  }

  const chooseQuickAction = (text: string) => {
    setMessage(`${text}: `)
  }

  if (isSessionLoading) {
    return <div className="loading-screen">Подготавливаем арену…</div>
  }

  return (
    <div className="app">
      <header className={`topbar topbar-${view}`}>
        <div className="brand">
          <div className="brand-logo">A</div>
          <div>
            <div className="brand-title">Арена переговоров</div>
            <div className="brand-subtitle">Тренажёр переговорных навыков</div>
          </div>
        </div>
        {view === 'active' && (
          <>
            <div className="topbar-context">
              <span className="eyebrow">Сценарий</span>
              <strong>{scenario?.name ?? 'Переговоры'}</strong>
            </div>
            <div className="timer-block">
              <span className="timer-label">Время</span>
              <strong>{formatDuration(elapsedSeconds)}</strong>
            </div>
          </>
        )}
      </header>

      {sessionError && <div className="global-error">{sessionError}</div>}

      {view === 'setup' && (
        <main className="setup-shell">
          <section className="setup-hero">
            <h1>Ведите переговоры<br /><span>уверенно</span></h1>
            <p>Выберите уровень поддержки и потренируйтесь на реалистичном сценарии.</p>
            <div className="setup-note">
              <svg aria-hidden="true" viewBox="0 0 24 24">
                <path d="M5 3.5h9l5 5V20a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" />
                <path d="M14 4v5h5M8 13h8M8 17h5" />
              </svg>
              <span>Делайте заметки по ходу диалога — они останутся только у вас.</span>
            </div>
          </section>

          <section className="setup-card">
            <div className="section-heading">
              <div>
                <span className="eyebrow">СЦЕНАРИЙ</span>
                <h2>{scenario?.name ?? 'Сценарий не найден'}</h2>
              </div>
              <span className="step-index">01</span>
            </div>
            <p className="card-description">{scenario?.description ?? 'Подготовка сценария переговоров.'}</p>
            <div className="scenario-meta">
              <span><b>Роль</b> {scenario?.character_role ?? 'Загрузка…'}</span>
              <span><b>Формат</b> Диалог с AI-оппонентом</span>
            </div>

            <div className="section-heading difficulty-heading">
              <div>
                <span className="eyebrow">СЛОЖНОСТЬ</span>
                <h2>Сколько поддержки вам нужно?</h2>
              </div>
              <span className="step-index">02</span>
            </div>
            <div className="difficulty-grid">
              {difficultyOptions.map((option) => (
                <button
                  key={option.id}
                  className={`difficulty-option ${difficulty === option.id ? 'selected' : ''}`}
                  onClick={() => setDifficulty(option.id)}
                >
                  <span className="difficulty-radio" />
                  <span>
                    <strong>{option.label}</strong>
                    <small>{option.description}</small>
                  </span>
                </button>
              ))}
            </div>
            <button className="primary-button start-button" onClick={() => void startNegotiation()} disabled={!scenario || isStarting}>
              {isStarting ? 'Подготавливаем…' : 'Начать переговоры'} <ArrowIcon />
            </button>
          </section>
        </main>
      )}

      {view === 'active' && (
        <main className={`active-shell ${selectedDifficulty.metricMode === 'hidden' ? 'metrics-hidden' : ''}`}>
          <section className="chat-panel">
            <div className="chat-header">
              <div>
                <span className="eyebrow">АРЕНА · {selectedDifficulty.label.toUpperCase()}</span>
                <h2>{scenario?.character_name ?? 'Собеседник'}</h2>
                <p>{scenario?.character_role ?? 'Представитель поставщика'} · {state?.turn_count ?? 0} ходов</p>
              </div>
              <div className="chat-header-actions">
                <span className="status-badge"><i /> Переговоры идут</span>
                <button className="finish-button" onClick={() => void completeSession()} disabled={isCompleting || isOpponentThinking}>
                  {isCompleting ? 'Завершаем…' : 'Завершить'}
                </button>
              </div>
            </div>

            <div className="messages">
              {messages.map((msg) => <Message key={msg.id} {...msg} />)}
              {isOpponentThinking && <Message author="Собеседник" text="Формулирует ответ…" time="" mine={false} />}
              <div ref={messagesEndRef} />
            </div>

            <div className="quick-actions">
              <button onClick={() => chooseQuickAction('Открытый вопрос')}>+ Открытый вопрос</button>
              <button onClick={() => chooseQuickAction('Уточнить интересы')}>◎ Уточнить интересы</button>
              <button onClick={() => chooseQuickAction('Аргумент на фактах')}>▣ Аргумент на фактах</button>
              <button onClick={() => chooseQuickAction('Предложить компромисс')}>◇ Компромисс</button>
            </div>

            <div className="message-input">
              <textarea
                placeholder="Сформулируйте вашу реплику…"
                value={message}
                maxLength={5000}
                disabled={isOpponentThinking || !sessionId}
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    void sendMessage()
                  }
                }}
              />
              <button onClick={() => void sendMessage()} disabled={isOpponentThinking || !message.trim() || !sessionId}>→</button>
            </div>
          </section>

          <aside className="active-side">
            {selectedDifficulty.metricMode === 'hidden' ? (
              <div className="coach-card quiet-card">
                <span className="card-icon">◌</span>
                <span className="eyebrow">РЕЖИМ ТРЕНЕРА</span>
                <h3>Слушайте разговор, а не шкалы</h3>
                <p>Live-метрики скрыты. После завершения вы получите полный разбор решений и динамики собеседника.</p>
              </div>
            ) : (
              <div className="side-card">
                <div className="side-card-heading"><span className="eyebrow">СИГНАЛЫ СОБЕСЕДНИКА</span><span className="live-dot">LIVE</span></div>
                <div className="side-metrics">
                  {activeMetrics.map((metric) => <Metric key={metric.key} title={metric.title} value={metrics[metric.key] ?? 0} variant={metric.variant} compact />)}
                </div>
                <p className="metric-hint">Показатели меняются после каждой вашей реплики.</p>
              </div>
            )}

            <div className="notes-card">
              <button className="notes-toggle" onClick={() => setIsNotesOpen((open) => !open)}>
                <span><span className="notes-icon">✎</span> Мои заметки</span><span>{isNotesOpen ? '−' : '+'}</span>
              </button>
              {isNotesOpen && <textarea value={notes} onChange={(event) => saveNotes(event.target.value)} placeholder="Что сработало? Где стоило выдержать паузу?" maxLength={5000} />}
              {!isNotesOpen && <p>Фиксируйте наблюдения по ходу разговора.</p>}
            </div>

            {state?.coach_message && selectedDifficulty.metricMode !== 'hidden' && (
              <div className="coach-card mini-coach">
                <span className="eyebrow">AI COACH</span>
                <p>{state.coach_message}</p>
              </div>
            )}
          </aside>
        </main>
      )}

      {view === 'completed' && result && (
        <main className="summary-shell">
          <section className="summary-hero">
            <div>
              <span className="eyebrow accent">СЕССИЯ ЗАВЕРШЕНА</span>
              <h1>{result.outcome === 'strong' ? 'Сильный раунд.' : result.outcome === 'acceptable' ? 'Хорошая основа для роста.' : 'Раунд завершён.'}</h1>
              <p>Разбор показывает не только итог, но и то, как ваши решения повлияли на ход переговоров.</p>
            </div>
            <div className="score-card"><span>ИТОГОВАЯ ОЦЕНКА</span><strong>{result.final_score}</strong><small>/ 100</small></div>
          </section>

          <div className="summary-grid">
            <section className="summary-card metrics-card">
              <div className="card-heading"><span className="eyebrow">ПАНЕЛЬ РАУНДА</span><span>{state?.turn_count ?? 0} ходов</span></div>
              <div className="summary-metrics">
                <Metric title="Доверие" value={result.final_metrics.trust ?? 0} variant="blue" />
                <Metric title="Интерес" value={result.final_metrics.interest ?? 0} variant="green" />
                <Metric title="Открытость" value={result.final_metrics.openness ?? 0} variant="green" />
                <Metric title="Риск срыва" value={result.final_metrics.risk ?? 0} variant="orange" />
                <Metric title="Раздражение" value={result.final_metrics.irritation ?? 0} variant="orange" />
                <Metric title="Напряжение" value={result.final_metrics.tension ?? 0} variant="blue" />
              </div>
            </section>

            <section className="summary-card insight-card">
              <div className="card-heading"><span className="eyebrow">AI COACH</span><span>ОБРАТНАЯ СВЯЗЬ</span></div>
              <div className="insight-columns">
                <div><h3>Сработало</h3>{result.strengths.map((item) => <p className="insight-positive" key={item}>✓ {item}</p>)}</div>
                <div><h3>Можно улучшить</h3>{result.mistakes.map((item) => <p className="insight-negative" key={item}>! {item}</p>)}</div>
              </div>
              <div className="recommendation"><span>Рекомендация</span><p>{result.recommendations[0]}</p></div>
            </section>
          </div>

          <section className="summary-card bottom-summary">
            <div className="card-heading"><span className="eyebrow">ДЕТАЛИ СЕССИИ</span><span>{state?.detected_tactics?.length ?? 0} техник</span></div>
            <div className="techniques">{(state?.detected_tactics ?? []).map((tactic) => <span key={tactic}>{tacticLabels[tactic] ?? tactic}</span>)}{!state?.detected_tactics?.length && <span>Техники не зафиксированы</span>}</div>
            {notes && <div className="saved-notes"><span className="eyebrow">ВАШИ ЗАМЕТКИ</span><p>{notes}</p></div>}
            <button className="transcript-toggle" onClick={() => setIsTranscriptOpen((open) => !open)}>{isTranscriptOpen ? 'Скрыть transcript' : 'Открыть transcript'} <span>{isTranscriptOpen ? '↑' : '↓'}</span></button>
            {isTranscriptOpen && <div className="transcript">{messages.map((msg) => <Message key={msg.id} {...msg} />)}</div>}
          </section>
          <button className="primary-button new-session-button" onClick={startNewSession}>Начать новую сессию <ArrowIcon /></button>
        </main>
      )}
    </div>
  )
}

export default App
