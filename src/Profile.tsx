import { Achievements } from './Achievements'
import { achievementTotal } from './achievementCatalog'

type ProfileSession = {
  session_id: string
  status: string
  scenario_id: string | null
  difficulty: string
  fork_from_turn: number | null
  notes: string
  result: {
    final_score: number
    completed_at: string
    strengths: string[]
    mistakes: string[]
    key_moments: string[]
    recommendations: string[]
    skills: Record<string, number>
    achievements: string[]
  } | null
}

type Props = {
  sessions: ProfileSession[]
  scenarioNames: Record<string, string>
  onOpen: (id: string) => void
  onSaveNotes: (id: string, value: string) => void
  onBack: () => void
  onAnalyze: () => void
  onOpenReport: () => void
  hasPreviousReport: boolean
  isAnalyzing: boolean
  error: string | null
}

const techniques = [
  {
    name: 'SPIN',
    tagline: 'Сначала разобраться, затем предлагать',
    description: 'Последовательность вопросов: ситуация → проблема → последствия → ценность решения. Помогает найти реальную потребность, а не спорить о первой названной позиции.',
    example: '«Что мешает вам уложиться в срок? Как это повлияет на запуск?»',
  },
  {
    name: 'BATNA',
    tagline: 'Знайте свою альтернативу',
    description: 'Лучший вариант действий, если договориться не получится. Сравнивайте предложение с этой альтернативой, чтобы не соглашаться на заведомо плохие условия.',
    example: '«Если мы не согласуем эту цену, какие у нас есть другие варианты?»',
  },
  {
    name: 'Гарвардский метод',
    tagline: 'Интересы важнее позиций',
    description: 'Отделяйте людей от проблемы, выясняйте интересы сторон, ищите взаимовыгодные варианты и опирайтесь на объективные критерии.',
    example: '«Что для вас важнее: срок поставки или минимальная цена?»',
  },
  {
    name: 'Обмен уступками',
    tagline: 'Уступка — часть сделки, не подарок',
    description: 'Связывайте каждое изменение условий со встречным шагом. Это помогает сохранить баланс интересов и проверить готовность другой стороны.',
    example: '«Если мы увеличим объём заказа, сможете пересмотреть цену?»',
  },
]

const axes = [
  ['questions', 'Вопросы'],
  ['empathy', 'Эмпатия'],
  ['argumentation', 'Аргументы'],
  ['flexibility', 'Гибкость'],
  ['self_control', 'Самоконтроль'],
] as const

function radarPoint(index: number, value: number, radius: number): [number, number] {
  const angle = -Math.PI / 2 + index * 2 * Math.PI / axes.length
  const distance = radius * value / 100
  return [150 + Math.cos(angle) * distance, 150 + Math.sin(angle) * distance]
}

function radarPoints(values: number[], radius: number) {
  return values.map((value, index) => radarPoint(index, value, radius).join(',')).join(' ')
}

function SkillsRadar({ sessions }: { sessions: ProfileSession[] }) {
  const rated = sessions.filter((item) => item.result && Object.keys(item.result.skills ?? {}).length)
  const values = axes.map(([key]) => rated.length
    ? Math.round(rated.reduce((sum, item) => sum + (item.result?.skills[key] ?? 0), 0) / rated.length)
    : 0)

  return (
    <div className="profile-radar-wrap">
      <svg className="profile-radar" viewBox="0 0 300 300" role="img" aria-label="Средние навыки переговорщика">
        {[25, 50, 75, 100].map((level) => <polygon key={level} points={radarPoints([level, level, level, level, level], 98)} className="radar-grid" />)}
        {axes.map((_, index) => <line key={index} x1="150" y1="150" x2={radarPoint(index, 100, 98)[0]} y2={radarPoint(index, 100, 98)[1]} className="radar-axis" />)}
        <polygon points={radarPoints(values, 98)} className="radar-area" />
        {values.map((value, index) => <circle key={axes[index][0]} cx={radarPoint(index, value, 98)[0]} cy={radarPoint(index, value, 98)[1]} r="4" className="radar-point" />)}
      </svg>
      <div className="radar-legend">{axes.map(([key, label], index) => <span key={key}>{label}<strong>{values[index]}</strong></span>)}</div>
    </div>
  )
}

export default function Profile({ sessions, scenarioNames, onOpen, onSaveNotes, onBack, onAnalyze, onOpenReport, hasPreviousReport, isAnalyzing, error }: Props) {
  const completed = sessions.filter((item) => item.status === 'completed' && item.result)
  const average = completed.length ? Math.round(completed.reduce((sum, item) => sum + (item.result?.final_score ?? 0), 0) / completed.length) : 0
  const best = completed.length ? Math.max(...completed.map((item) => item.result?.final_score ?? 0)) : 0
  const unlockedAchievements = [...new Set(completed.flatMap((item) => item.result?.achievements ?? []))]

  return (
    <main className="profile-shell">
      <button className="profile-back" onClick={onBack}>← Вернуться на арену</button>
      <div className="profile-heading"><div><h1>Личный кабинет</h1><p>История попыток и заметки этого браузера. Аккаунт и синхронизацию добавим позже.</p></div></div>
      <div className="profile-stats">
        <div><span>Попыток</span><strong>{sessions.length}</strong></div>
        <div><span>Завершено</span><strong>{completed.length}</strong></div>
        <div><span>Средний балл</span><strong>{average}</strong></div>
        <div><span>Лучший раунд</span><strong>{best}</strong></div>
      </div>
      {completed.length > 0 && <section className="profile-panel profile-achievements">
        <div className="card-heading"><span className="eyebrow">ДОСТИЖЕНИЯ</span><span>{unlockedAchievements.length} из {achievementTotal} открыто</span></div>
        <h2>Ваши достижения</h2>
        <Achievements unlocked={unlockedAchievements} alignWithProfile />
      </section>}
      <div className="profile-grid">
        <section className="profile-panel"><span className="eyebrow">ПРОФИЛЬ НАВЫКОВ</span><h2>Ваш стиль переговоров</h2><SkillsRadar sessions={completed} /><p className="profile-muted">Диаграмма строится по завершённым раундам. Оценки приблизительные и помогают видеть динамику.</p><button className="profile-analyze-button" onClick={onAnalyze} disabled={!completed.length || isAnalyzing}>{isAnalyzing ? 'Запускаем анализ…' : 'Разобрать мои навыки'} <span aria-hidden="true">↗</span></button>{hasPreviousReport && <button className="profile-previous-report" onClick={onOpenReport}>Открыть последний отчёт →</button>}{error && <p className="profile-analysis-error" role="alert">{error}</p>}<p className="profile-muted">{completed.length ? 'Разберём до 20 последних завершённых раундов. На этой ВМ генерация может занять около минуты.' : 'Завершите хотя бы один раунд, чтобы получить разбор.'}</p></section>
        <section className="profile-panel"><span className="eyebrow">ИСТОРИЯ</span><h2>Ваши попытки</h2>
          {sessions.length === 0 && <p className="profile-muted">Пока нет попыток. Начните переговоры, чтобы увидеть здесь результат.</p>}
          <div className="profile-history">{sessions.map((session) => <article className="profile-attempt" key={session.session_id}>
            <div className="profile-attempt-top"><div><strong>{scenarioNames[session.scenario_id ?? ''] ?? 'Переговоры'}</strong><span>{session.result ? new Date(session.result.completed_at).toLocaleDateString('ru-RU') : 'Раунд не завершён'} · {session.difficulty}{session.fork_from_turn ? ` · ветка с хода ${session.fork_from_turn}` : ''}</span></div><span className="profile-attempt-score">{session.result ? `${session.result.final_score}/100` : 'В процессе'}</span></div>
            {session.result && <details><summary>Выжимка и заметки</summary><div className="profile-summary-columns"><div><b>Сильные стороны</b>{session.result.strengths.length ? session.result.strengths.map((text) => <p key={text}>{text}</p>) : <p>Пока нет отмеченных сильных сторон.</p>}</div><div><b>Что улучшить</b>{session.result.mistakes.map((text) => <p key={text}>{text}</p>)}</div></div>{session.result.key_moments.length > 0 && <div className="profile-key-moments"><b>Ключевые моменты</b>{session.result.key_moments.map((text) => <p key={text}>{text}</p>)}</div>}{session.result.recommendations?.length > 0 && <div className="profile-key-moments"><b>Рекомендации</b>{session.result.recommendations.map((text) => <p key={text}>{text}</p>)}</div>}<div className="profile-key-moments"><label htmlFor={`profile-notes-${session.session_id}`}><b>Ваши заметки</b></label><textarea id={`profile-notes-${session.session_id}`} key={session.session_id} defaultValue={session.notes} onBlur={(event) => onSaveNotes(session.session_id, event.currentTarget.value)} maxLength={5000} placeholder="Что получилось? Что вы измените в следующий раз?" /></div></details>}
            {!session.result && <div className="profile-key-moments"><label htmlFor={`profile-notes-${session.session_id}`}><b>Ваши заметки</b></label><textarea id={`profile-notes-${session.session_id}`} key={session.session_id} defaultValue={session.notes} onBlur={(event) => onSaveNotes(session.session_id, event.currentTarget.value)} maxLength={5000} placeholder="Запишите наблюдения по этому раунду" /></div>}
            <button className="profile-open" onClick={() => onOpen(session.session_id)}>{session.status === 'completed' ? 'Открыть разбор' : 'Продолжить раунд'} →</button>
          </article>)}</div>
        </section>
      </div>
      <section className="profile-panel profile-techniques"><span className="eyebrow">АРСЕНАЛ ПЕРЕГОВОРЩИКА</span><h2>Как работают техники</h2><p className="profile-muted">Короткие ориентиры: когда применять приём и как он звучит в разговоре.</p><div className="profile-techniques-grid">{techniques.map((technique) => <details className="profile-technique" key={technique.name}><summary><span><strong>{technique.name}</strong><small>{technique.tagline}</small></span><span className="profile-technique-plus" aria-hidden="true">+</span></summary><p>{technique.description}</p><div className="profile-technique-example"><span>Пример реплики</span><p>{technique.example}</p></div></details>)}</div></section>
    </main>
  )
}
