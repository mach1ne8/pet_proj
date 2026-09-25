import { useEffect, useMemo, useRef, useState } from 'react'
import Profile from './Profile'
import './index.css'

const SESSION_STORAGE_KEY = 'negotiation_session_id'
const DIFFICULTY_STORAGE_KEY = 'negotiation_difficulty'
const NOTES_STORAGE_PREFIX = 'negotiation_notes_'
const SESSION_STARTED_PREFIX = 'negotiation_started_at_'
const SESSION_IDS_KEY = 'negotiation_session_ids'

type View = 'setup' | 'active' | 'completed' | 'profile'
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
  key_moments: string[]
  skills: Record<string, number>
  analysis_status: 'pending' | 'ready' | 'failed'
  completed_at: string
}

type SessionResponse = {
  session_id: string
  status: 'active' | 'completed' | 'abandoned'
  scenario_id: string | null
  difficulty: Difficulty
  expires_at: string | null
  hints_used: number
  hint_history: string[]
  batna_revealed: boolean
  batna_text: string | null
  notes: string
  parent_session_id: string | null
  fork_from_turn: number | null
  state: SessionState | null
  result: SessionResult | null
  messages: ApiMessage[]
}

type ChatResponse = {
  message: string
  state: SessionState
  batna_revealed: boolean
  batna_text: string | null
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
  metricMode: 'emotional' | 'full' | 'qualitative' | 'hidden'
}> = [
  {
    id: 'beginner',
    label: 'Новичок',
    description: 'Эмоциональный барометр и поддержка AI-коуча.',
    metricMode: 'emotional',
  },
  {
    id: 'analyst',
    label: 'Аналитик',
    description: 'Полные метрики состояния собеседника.',
    metricMode: 'full',
  },
  {
    id: 'advanced',
    label: 'Переговорщик',
    description: 'Без чисел: только ход разговора и ваши заметки.',
    metricMode: 'qualitative',
  },
  {
    id: 'expert',
    label: 'Мастер',
    description: 'Без метрик и подсказок во время разговора.',
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

function ArenaMark({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 620 590"
      fill="none"
    >
      <defs>
        <linearGradient id="arena-glass-body" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="white" stopOpacity=".58" />
          <stop offset="38%" stopColor="#aac7e8" stopOpacity=".48" />
          <stop offset="72%" stopColor="#e8f2ff" stopOpacity=".32" />
          <stop offset="100%" stopColor="#769bd0" stopOpacity=".48" />
        </linearGradient>
        <linearGradient id="arena-glass-blue" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#79aaff" stopOpacity=".76" />
          <stop offset="52%" stopColor="#2563eb" stopOpacity=".62" />
          <stop offset="100%" stopColor="#174ab6" stopOpacity=".7" />
        </linearGradient>
        <linearGradient id="arena-glass-sheen" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="white" stopOpacity=".56" />
          <stop offset="48%" stopColor="white" stopOpacity=".14" />
          <stop offset="100%" stopColor="white" stopOpacity="0" />
        </linearGradient>
        <clipPath id="arena-glass-clip">
          <path d="M18 568 277 48c14-29 52-29 67 0l112 211-71 41-76-142L106 568H18Zm394-190 72-42 118 232H500l-88-190Z" />
          <path d="m153 550 45-87 277-157 37 62-314 182h-45Z" />
        </clipPath>
      </defs>
      <path
        className="arena-mark-main"
        d="M18 568 277 48c14-29 52-29 67 0l112 211-71 41-76-142L106 568H18Zm394-190 72-42 118 232H500l-88-190Z"
      />
      <path
        className="arena-mark-accent"
        d="m153 550 45-87 277-157 37 62-314 182h-45Z"
      />
      {className === 'setup-watermark-mark' && (
        <g className="arena-mark-glass-sheen" clipPath="url(#arena-glass-clip)">
          <path d="M0 0h620v590H0z" fill="url(#arena-glass-sheen)" />
        </g>
      )}
    </svg>
  )
}

function Message({
  author,
  text,
  time,
  mine,
  anchorId,
  onRewind,
}: {
  author: string
  text: string
  time: string
  mine: boolean
  anchorId?: string
  onRewind?: () => void
}) {
  return (
    <div id={anchorId} className={`message-row ${mine ? 'mine' : ''}`}>
      <div className="avatar">{mine ? 'В' : 'С'}</div>
      <div className={`message ${mine ? 'message-mine' : ''}`}>
        <div className="message-meta">
          <strong>{author}</strong>
          <span>{time}</span>
        </div>
        <div className="message-text">{text}</div>
        {onRewind && <button className="message-reply" onClick={onRewind} aria-label="Вернуться к этому ходу">↶ Вернуться к ходу</button>}
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

function getStoredSessionIds(): string[] {
  try {
    const stored = JSON.parse(localStorage.getItem(SESSION_IDS_KEY) ?? '[]')
    return Array.isArray(stored) ? stored.filter((id): id is string => typeof id === 'string') : []
  } catch {
    return []
  }
}

function rememberSession(id: string) {
  localStorage.setItem(SESSION_IDS_KEY, JSON.stringify([...new Set([id, ...getStoredSessionIds()])]))
}

function App() {
  const [view, setView] = useState<View>('setup')
  const [difficulty, setDifficulty] = useState<Difficulty>(getStoredDifficulty)
  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessionStatus, setSessionStatus] = useState<'active' | 'completed' | 'abandoned' | null>(null)
  const [expiresAt, setExpiresAt] = useState<string | null>(null)
  const [remainingSeconds, setRemainingSeconds] = useState(600)
  const [hintsUsed, setHintsUsed] = useState(0)
  const [hintMessages, setHintMessages] = useState<string[]>([])
  const [batnaText, setBatnaText] = useState<string | null>(null)
  const [profileSessions, setProfileSessions] = useState<SessionResponse[]>([])
  const [isHintLoading, setIsHintLoading] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [state, setState] = useState<SessionState | null>(null)
  const [result, setResult] = useState<SessionResult | null>(null)
  const [message, setMessage] = useState('')
  const [notes, setNotes] = useState('')
  const [parentSessionId, setParentSessionId] = useState<string | null>(null)
  const [forkFromTurn, setForkFromTurn] = useState<number | null>(null)
  const [rewindTarget, setRewindTarget] = useState<number | null>(null)
  const [isRewinding, setIsRewinding] = useState(false)
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
  const notesTimerRef = useRef<number | null>(null)
  const previousViewRef = useRef<View>('setup')

  const selectedDifficulty = useMemo(
    () => difficultyOptions.find((item) => item.id === difficulty)!,
    [difficulty],
  )

  const metrics = state?.metrics ?? {}
  const emotionalMetrics = [
    { title: 'Раздражение', key: 'irritation', variant: 'orange' as const },
    { title: 'Интерес', key: 'interest', variant: 'blue' as const },
    { title: 'Напряжение', key: 'tension', variant: 'orange' as const },
    { title: 'Открытость', key: 'openness', variant: 'blue' as const },
  ]
  const analystMetrics = [
    { title: 'Доверие', key: 'trust', variant: 'blue' as const },
    ...emotionalMetrics,
    { title: 'Риск срыва', key: 'risk', variant: 'orange' as const },
  ]
  const tacticSet = new Set(state?.detected_tactics ?? [])
  const checklist = [
    { title: 'SPIN', done: tacticSet.has('open_question') || tacticSet.has('spin') },
    { title: 'BATNA', done: Boolean(batnaText) || tacticSet.has('batna') },
    { title: 'Гарвардский метод', done: ['empathy', 'tradeoff', 'compromise', 'principled_negotiation'].some((item) => tacticSet.has(item)) },
  ]
  const achievementCount = Number((state?.turn_count ?? 0) > 0) + Number(tacticSet.has('open_question')) + Number(Boolean(batnaText))
  const latestOpponentText = [...messages].reverse().find((item) => !item.mine)?.text ?? ''
  const playerTurns = messages.filter((item) => item.mine)

  const saveNotes = (value: string) => {
    setNotes(value)
    if (sessionId) {
      localStorage.setItem(`${NOTES_STORAGE_PREFIX}${sessionId}`, value)
      if (notesTimerRef.current) window.clearTimeout(notesTimerRef.current)
      notesTimerRef.current = window.setTimeout(() => {
        void fetch(`/api/sessions/${sessionId}/notes`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ notes: value }),
        }).then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`)
        }).catch(() => setSessionError('Не удалось сохранить заметки на сервере'))
      }, 500)
    }
  }

  const applySession = (data: SessionResponse, availableScenarios = scenarios) => {
    rememberSession(data.session_id)
    localStorage.setItem(SESSION_STORAGE_KEY, data.session_id)
    setSessionId(data.session_id)
    setSessionStatus(data.status)
    setDifficulty(data.difficulty)
    setExpiresAt(data.expires_at)
    setHintsUsed(data.hints_used)
    setHintMessages(data.hint_history ?? [])
    setParentSessionId(data.parent_session_id)
    setForkFromTurn(data.fork_from_turn)
    setRewindTarget(null)
    setBatnaText(data.batna_revealed ? data.batna_text : null)
    setMessages(mapApiMessages(data.messages))
    setState(data.state)
    setResult(data.result)
    setScenario((current) => (
      availableScenarios.find((item) => item.id === data.scenario_id) ?? current
    ))
    const storedNotes = localStorage.getItem(`${NOTES_STORAGE_PREFIX}${data.session_id}`)
    setNotes(storedNotes ?? data.notes ?? '')
    if (data.status === 'completed') {
      const savedStartedAt = localStorage.getItem(`${SESSION_STARTED_PREFIX}${data.session_id}`)
      if (savedStartedAt && data.result) {
        setElapsedSeconds(Math.max(0, Math.floor((new Date(data.result.completed_at).getTime() - Number(savedStartedAt)) / 1000)))
      } else {
        setElapsedSeconds(0)
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
      setRemainingSeconds(data.expires_at ? Math.max(0, Math.ceil((new Date(data.expires_at).getTime() - Date.now()) / 1000)) : 600)
    }
  }

  const fetchScenarios = async () => {
    const response = await fetch('/api/scenarios')
    if (!response.ok) throw new Error(`Ошибка загрузки сценариев: HTTP ${response.status}`)
    const data: Scenario[] = await response.json()
    setScenarios(data)
    setScenario((current) => current ?? data[0] ?? null)
    return data
  }

  const createSession = async (scenarioId?: string) => {
    const response = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_id: scenarioId, difficulty }),
    })
    if (!response.ok) throw new Error(`Ошибка создания сессии: HTTP ${response.status}`)
    const data: SessionResponse = await response.json()
    localStorage.setItem(SESSION_STORAGE_KEY, data.session_id)
    rememberSession(data.session_id)
    const sessionStartedAt = Date.now()
    localStorage.setItem(`${SESSION_STARTED_PREFIX}${data.session_id}`, String(sessionStartedAt))
    applySession(data)
    setView('active')
    setStartedAt(sessionStartedAt)
  }

  const restoreSession = async (storedSessionId: string, availableScenarios = scenarios) => {
    const response = await fetch(`/api/sessions/${storedSessionId}`)
    if (response.status === 404) {
      localStorage.removeItem(SESSION_STORAGE_KEY)
      return
    }
    if (!response.ok) throw new Error(`Ошибка восстановления сессии: HTTP ${response.status}`)
    const data: SessionResponse = await response.json()
    applySession(data, availableScenarios)
  }

  const loadProfile = async () => {
    const ids = getStoredSessionIds()
    const loaded = await Promise.all(ids.map(async (id) => {
      try {
        const response = await fetch(`/api/sessions/${id}`)
        return response.ok ? await response.json() as SessionResponse : null
      } catch {
        return null
      }
    }))
    setProfileSessions(loaded.filter((item): item is SessionResponse => item !== null && item.expires_at !== null).sort((a, b) =>
      (b.result?.completed_at ?? b.expires_at ?? '').localeCompare(a.result?.completed_at ?? a.expires_at ?? ''),
    ))
  }

  const saveProfileNotes = async (id: string, value: string) => {
    localStorage.setItem(`${NOTES_STORAGE_PREFIX}${id}`, value)
    setProfileSessions((current) => current.map((item) => item.session_id === id ? { ...item, notes: value } : item))
    if (id === sessionId) setNotes(value)
    try {
      const response = await fetch(`/api/sessions/${id}/notes`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: value }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
    } catch {
      setSessionError('Не удалось сохранить заметки на сервере')
    }
  }

  const openProfile = () => {
    previousViewRef.current = view
    window.history.pushState({}, '', '/profile')
    setView('profile')
    void loadProfile()
  }

  const closeProfile = () => {
    window.history.pushState({}, '', '/')
    setView(previousViewRef.current === 'profile'
      ? sessionStatus === 'active' ? 'active' : result ? 'completed' : 'setup'
      : previousViewRef.current)
  }

  const openProfileSession = async (id: string) => {
    try {
      const response = await fetch(`/api/sessions/${id}`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      applySession(await response.json() as SessionResponse)
      window.history.pushState({}, '', '/')
    } catch {
      setSessionError('Не удалось открыть попытку')
    }
  }

  useEffect(() => {
    if (sessionStartedRef.current) return
    sessionStartedRef.current = true

    const initialize = async () => {
      try {
        setIsSessionLoading(true)
        const availableScenarios = await fetchScenarios()
        const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)
        if (storedSessionId) await restoreSession(storedSessionId, availableScenarios)
        if (window.location.pathname === '/profile') {
          await loadProfile()
          setView('profile')
        }
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
    const handlePopState = () => {
      if (window.location.pathname === '/profile') {
        void loadProfile()
        setView('profile')
      } else {
        setView(sessionStatus === 'active' ? 'active' : result ? 'completed' : 'setup')
      }
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [sessionStatus, result])

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
      if (response.status === 409) {
        await restoreSession(sessionId)
        return
      }
      if (!response.ok) throw new Error(`Ошибка API: HTTP ${response.status}`)

      const data: ChatResponse = await response.json()
      setState(data.state)
      setBatnaText(data.batna_revealed ? data.batna_text : null)
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
      setMessages((prev) => prev.filter((item) => item.id !== userMessage.id))
      setMessage(text)
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

  const rewindToTurn = async (turn: number) => {
    if (!sessionId || isRewinding || isOpponentThinking || remainingSeconds === 0) return
    const selected = playerTurns[turn - 1]
    if (!selected) return
    try {
      setIsRewinding(true)
      setSessionError(null)
      const response = await fetch(`/api/sessions/${sessionId}/fork`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ turn_count: turn, notes }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const branch: SessionResponse = await response.json()
      const originalStart = localStorage.getItem(`${SESSION_STARTED_PREFIX}${sessionId}`)
      if (originalStart) localStorage.setItem(`${SESSION_STARTED_PREFIX}${branch.session_id}`, originalStart)
      applySession(branch)
      setMessage(selected.text)
      setView('active')
    } catch (error) {
      console.error('Ошибка отката:', error)
      setSessionError('Не удалось вернуться к выбранному ходу. Попробуйте ещё раз.')
    } finally {
      setIsRewinding(false)
    }
  }

  const startNewSession = () => {
    localStorage.removeItem(SESSION_STORAGE_KEY)
    setSessionId(null)
    setSessionStatus(null)
    setExpiresAt(null)
    setStartedAt(null)
    setElapsedSeconds(0)
    setHintsUsed(0)
    setHintMessages([])
    setBatnaText(null)
    setMessages([])
    setState(null)
    setResult(null)
    setNotes('')
    setParentSessionId(null)
    setForkFromTurn(null)
    setRewindTarget(null)
    setMessage('')
    setSessionError(null)
    setIsTranscriptOpen(false)
    window.history.pushState({}, '', '/')
    setView('setup')
  }

  const chooseQuickAction = async (tactic: string) => {
    if (!sessionId || isGenerating || isOpponentThinking) return
    try {
      setIsGenerating(true)
      const response = await fetch(`/api/sessions/${sessionId}/suggest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tactic }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data: { message: string } = await response.json()
      setMessage(data.message)
    } catch {
      setSessionError('Не удалось предложить реплику. Попробуйте ещё раз.')
    } finally {
      setIsGenerating(false)
    }
  }

  const requestHint = async () => {
    if (!sessionId || isHintLoading) return
    try {
      setIsHintLoading(true)
      const response = await fetch(`/api/sessions/${sessionId}/hint`, { method: 'POST' })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data: { message: string; hints_used: number; history: string[] } = await response.json()
      setHintMessages(data.history)
      setHintsUsed(data.hints_used)
    } catch {
      setSessionError('Подсказка сейчас недоступна')
    } finally {
      setIsHintLoading(false)
    }
  }

  useEffect(() => {
    if (view !== 'active' || !expiresAt) return
    const tick = () => {
      const remaining = Math.max(0, Math.ceil((new Date(expiresAt).getTime() - Date.now()) / 1000))
      setRemainingSeconds(remaining)
      if (startedAt) setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)))
      if (remaining === 0 && sessionStatus === 'active' && !isOpponentThinking && !isCompleting) void completeSession()
    }
    tick()
    const timer = window.setInterval(tick, 1000)
    return () => window.clearInterval(timer)
    // The deadline is authoritative; completion is idempotent on the server.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, expiresAt, startedAt, sessionStatus, isOpponentThinking, isCompleting])

  useEffect(() => {
    if (view !== 'completed' || !sessionId || result?.analysis_status !== 'pending') return
    let stopped = false
    const refreshAnalysis = async () => {
      try {
        const response = await fetch(`/api/sessions/${sessionId}`)
        if (!response.ok) return
        const data: SessionResponse = await response.json()
        if (!stopped && data.result) setResult(data.result)
      } catch {
        // Keep the saved preliminary report visible and retry on the next tick.
      }
    }
    const timer = window.setInterval(() => void refreshAnalysis(), 3000)
    return () => { stopped = true; window.clearInterval(timer) }
  }, [view, sessionId, result?.analysis_status])

  if (isSessionLoading) {
    return <div className="loading-screen">Подготавливаем арену…</div>
  }

  return (
    <div className={`app${view === 'setup' ? ' app-setup' : ''}`}>
      {view === 'setup' && (
        <div className="setup-glass-backdrop" aria-hidden="true">
          <ArenaMark className="setup-watermark-mark" />
        </div>
      )}
      <header className={`topbar topbar-${view}`}>
        <div className="brand">
          <div className="brand-logo"><ArenaMark /></div>
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
            <div className="achievements" title="Достижения за раунд" aria-label={`Достижений: ${achievementCount}`}>
              <span aria-hidden="true">✦</span><strong>{achievementCount}</strong><small>ачивки</small>
            </div>
            <div className="timer-block">
              <span className="timer-label">Осталось</span>
              <strong>{expiresAt ? formatDuration(remainingSeconds) : '—:—'}</strong>
            </div>
          </>
        )}
        <button className="account-placeholder" onClick={view === 'profile' ? closeProfile : openProfile} aria-label={view === 'profile' ? 'Вернуться на арену' : 'Открыть личный кабинет'} title="Личный кабинет">
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <circle cx="12" cy="8" r="3.5" />
            <path d="M5.5 20a6.5 6.5 0 0 1 13 0" />
          </svg>
        </button>
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
              <span>Делайте заметки по ходу диалога — они сохранятся вместе с раундом.</span>
            </div>
          </section>

          <section className="setup-card">
            {sessionStatus === 'active' && sessionId && <div className="resume-session"><span>Есть незавершённый раунд</span><button onClick={() => void restoreSession(sessionId)}>Продолжить →</button></div>}
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
                  aria-pressed={difficulty === option.id}
                  onClick={() => setDifficulty(option.id)}
                >
                  <span>
                    <strong>{option.label}</strong>
                    <small>{option.description}</small>
                  </span>
                  {difficulty === option.id && (
                    <span className="selection-check" aria-hidden="true">
                      <svg viewBox="0 0 20 20"><path d="m5 10 3.2 3.2L15.5 6" /></svg>
                    </span>
                  )}
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
        <main className={`active-shell mode-${selectedDifficulty.metricMode}`}>
          <aside className="active-left">
            <div className="side-card batna-card">
              <span className="eyebrow">СКРЫТАЯ ЦЕЛЬ · BATNA</span>
              {batnaText ? <><h3>Альтернатива раскрыта</h3><p>{batnaText}</p></> : <><h3>Пока неизвестна</h3><p>Уточняйте, какие альтернативы есть у собеседника, если договориться не получится.</p></>}
            </div>
            {selectedDifficulty.metricMode === 'emotional' && <div className="side-card emotional-card">
              <div className="side-card-heading"><span className="eyebrow">ЭМОЦИОНАЛЬНЫЙ БАРОМЕТР</span><span className="live-dot">LIVE</span></div>
              <p className="metric-hint">Чувства собеседника во время разговора</p>
              <div className="side-metrics">{emotionalMetrics.map((item) => <Metric key={item.key} title={item.title} value={metrics[item.key] ?? 0} variant={item.variant} compact />)}</div>
            </div>}
            <div className="side-card turn-history-card">
              <span className="eyebrow">ВАШИ ХОДЫ</span>
              <p className="metric-hint">Выберите реплику, к которой хотите вернуться.</p>
              {playerTurns.length === 0 ? <p className="turn-history-empty">Пока нет ваших реплик.</p> : <div className="turn-history-list">
                {playerTurns.map((item, index) => <button key={item.id} className={`turn-history-item ${rewindTarget === index + 1 ? 'selected' : ''}`} onClick={() => {
                  setRewindTarget(index + 1)
                  document.getElementById(`turn-${index + 1}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                }} disabled={isOpponentThinking || isRewinding}>
                  <span>Ход {index + 1} · {item.time}</span><strong>{item.text}</strong>
                </button>)}
              </div>}
              {rewindTarget !== null && <div className="rewind-confirm">
                <p>Создать новую ветку перед ходом {rewindTarget}? Исходный диалог сохранится.</p>
                <button onClick={() => void rewindToTurn(rewindTarget)} disabled={isRewinding || isOpponentThinking || remainingSeconds === 0}>{isRewinding ? 'Возвращаемся…' : 'Вернуться и изменить ответ'}</button>
                <button className="rewind-cancel" onClick={() => setRewindTarget(null)}>Отмена</button>
              </div>}
              {parentSessionId && <button className="branch-parent-link" onClick={() => void restoreSession(parentSessionId)}>← Исходная ветка</button>}
            </div>
          </aside>
          <section className="chat-panel">
            <div className="chat-header">
              <div>
                <button className="back-to-setup" onClick={() => setView('setup')}>← К настройке</button>
                <span className="eyebrow">АРЕНА · {selectedDifficulty.label.toUpperCase()}</span>
                <h2>{scenario?.character_name ?? 'Собеседник'}</h2>
                <p>{scenario?.character_role ?? 'Представитель поставщика'} · {state?.turn_count ?? 0} ходов{forkFromTurn ? ` · Ветка с хода ${forkFromTurn}` : ''}</p>
              </div>
              <div className="chat-header-actions">
                <span className="status-badge"><i /> Переговоры идут</span>
                <button className="finish-button" onClick={() => void completeSession()} disabled={isCompleting || isOpponentThinking}>
                  {isCompleting ? 'Завершаем…' : 'Завершить'}
                </button>
              </div>
            </div>

            <div className="messages">
              {messages.map((msg) => <Message key={msg.id} {...msg} anchorId={msg.mine ? `turn-${playerTurns.findIndex((item) => item.id === msg.id) + 1}` : undefined} onRewind={msg.mine ? () => setRewindTarget(playerTurns.findIndex((item) => item.id === msg.id) + 1) : undefined} />)}
              {isOpponentThinking && <Message author="Собеседник" text="Формулирует ответ…" time="" mine={false} />}
              <div ref={messagesEndRef} />
            </div>

            <div className="quick-actions">
              <button disabled={isGenerating || isOpponentThinking} onClick={() => void chooseQuickAction('open_question')}>+ Открытый вопрос</button>
              <button disabled={isGenerating || isOpponentThinking} onClick={() => void chooseQuickAction('interests')}>◎ Уточнить интересы</button>
              <button disabled={isGenerating || isOpponentThinking} onClick={() => void chooseQuickAction('facts')}>▣ Аргумент на фактах</button>
              <button disabled={isGenerating || isOpponentThinking} onClick={() => void chooseQuickAction('compromise')}>◇ Компромисс</button>
            </div>
            {isGenerating && <p className="generation-status">Готовим реплику для вас…</p>}

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
            {selectedDifficulty.metricMode === 'full' && (
              <div className="side-card">
                <div className="side-card-heading"><span className="eyebrow">СОСТОЯНИЕ СОБЕСЕДНИКА</span><span className="live-dot">LIVE</span></div>
                <div className="side-metrics">
                  {analystMetrics.map((metric) => <Metric key={metric.key} title={metric.title} value={metrics[metric.key] ?? 0} variant={metric.variant} compact />)}
                </div>
                <p className="metric-hint">Показатели меняются после каждой вашей реплики.</p>
              </div>
            )}
            {selectedDifficulty.metricMode === 'qualitative' && <div className="coach-card quiet-card"><span className="eyebrow">РЕЖИМ ПЕРЕГОВОРЩИКА</span><h3>Читайте между строк</h3><p>Последний сигнал собеседника:</p><blockquote>{latestOpponentText.slice(0, 170)}{latestOpponentText.length > 170 ? '…' : ''}</blockquote><p>Сделайте вывод сами. Числа появятся после раунда.</p></div>}

            {['emotional', 'full'].includes(selectedDifficulty.metricMode) && <div className="side-card sos-card"><span className="eyebrow">AI COACH</span><button onClick={() => void requestHint()} disabled={isHintLoading || hintsUsed >= 3}>{isHintLoading ? 'Готовим подсказку…' : `SOS · Подсказка ${hintsUsed}/3`}</button><p>Каждая подсказка уменьшает итоговую оценку на 8 баллов.</p><div aria-live="polite">{hintMessages.map((item, index) => ({ item, number: index + 1 })).reverse().map(({ item, number }) => <div className="sos-answer" key={`${number}-${item}`}><strong>Подсказка {number}</strong><span>{item}</span></div>)}</div></div>}

            <div className="side-card checklist-card"><span className="eyebrow">ЧЕК-ЛИСТ ТЕХНИК</span>{checklist.map((item) => <div className="checklist-item" key={item.title}><span className={item.done ? 'done' : ''}>{item.done ? '✓' : '○'}</span>{item.title}</div>)}</div>

            <div className="notes-card">
              <button className="notes-toggle" onClick={() => setIsNotesOpen((open) => !open)}>
                <span><span className="notes-icon">✎</span> Мои заметки</span><span>{isNotesOpen ? '−' : '+'}</span>
              </button>
              {isNotesOpen && <textarea value={notes} onChange={(event) => saveNotes(event.target.value)} placeholder="Что сработало? Где стоило выдержать паузу?" maxLength={5000} />}
              {!isNotesOpen && <p>Фиксируйте наблюдения по ходу разговора.</p>}
            </div>

          </aside>
        </main>
      )}

      {view === 'completed' && result && (
        <main className="summary-shell">
          {result.analysis_status === 'pending' && <div className="analysis-status">AI-анализ готовится. Предварительный разбор уже сохранён; эта страница обновится сама.</div>}
          {result.analysis_status === 'failed' && <div className="analysis-status">AI-анализ сейчас недоступен. Показан сохранённый предварительный разбор.</div>}
          <section className="summary-hero">
            <div>
              <span className="eyebrow accent">СЕССИЯ ЗАВЕРШЕНА</span>
              <h1>{result.outcome === 'unplayed' ? 'Диалог не состоялся.' : result.outcome === 'strong' ? 'Сильный раунд.' : result.outcome === 'acceptable' ? 'Хорошая основа для роста.' : 'Раунд завершён.'}</h1>
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
            <p className="round-duration">Время раунда: {formatDuration(Math.min(elapsedSeconds, 600))} · Подсказок SOS: {hintsUsed}</p>
            <div className="techniques">{(state?.detected_tactics ?? []).map((tactic) => <span key={tactic}>{tacticLabels[tactic] ?? tactic}</span>)}{!state?.detected_tactics?.length && <span>Техники не зафиксированы</span>}</div>
            {result.key_moments?.length > 0 && <div className="key-moments"><span className="eyebrow">КЛЮЧЕВЫЕ МОМЕНТЫ</span>{result.key_moments.map((item) => <p key={item}>{item}</p>)}</div>}
            {sessionId && <div className="saved-notes"><label className="eyebrow" htmlFor="summary-notes">ВАШИ ЗАМЕТКИ</label><textarea id="summary-notes" value={notes} onChange={(event) => saveNotes(event.target.value)} maxLength={5000} placeholder="Запишите, что получилось и что стоит попробовать иначе." /></div>}
            <button className="transcript-toggle" onClick={() => setIsTranscriptOpen((open) => !open)}>{isTranscriptOpen ? 'Скрыть transcript' : 'Открыть transcript'} <span>{isTranscriptOpen ? '↑' : '↓'}</span></button>
            {isTranscriptOpen && <div className="transcript">{messages.map((msg) => <Message key={msg.id} {...msg} />)}</div>}
          </section>
          <button className="primary-button new-session-button" onClick={startNewSession}>Начать новую сессию <ArrowIcon /></button>
        </main>
      )}
      {view === 'profile' && <Profile sessions={profileSessions.map((item) => ({ ...item, notes: localStorage.getItem(`${NOTES_STORAGE_PREFIX}${item.session_id}`) ?? item.notes ?? '' }))} scenarioNames={Object.fromEntries(scenarios.map((item) => [item.id, item.name]))} onOpen={(id) => void openProfileSession(id)} onSaveNotes={(id, value) => void saveProfileNotes(id, value)} onBack={closeProfile} />}
    </div>
  )
}

export default App
