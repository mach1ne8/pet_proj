import { useEffect } from 'react'

export type ProfileReport = {
  report_id: string
  status: 'pending' | 'ready' | 'failed'
  analysis: {
    summary: string
    strengths: string[]
    growth_areas: string[]
    next_steps: string[]
    rounds_analyzed: number
  } | null
}

type Props = {
  report: ProfileReport | null
  error: string | null
  onBack: () => void
  onRetry: () => void
  isRetrying: boolean
}

export default function ProfileAnalysis({ report, error, onBack, onRetry, isRetrying }: Props) {
  const analysis = report?.status === 'ready' ? report.analysis : null
  const failed = report?.status === 'failed' || !!error

  useEffect(() => {
    if (!analysis) return
    const previousTitle = document.title
    document.title = 'Анализ навыков — Арена переговоров'
    return () => { document.title = previousTitle }
  }, [analysis])

  return (
    <main className="profile-shell profile-analysis-shell">
      <div className="profile-analysis-toolbar">
        <button className="profile-back" onClick={onBack}>← Вернуться в личный кабинет</button>
        {analysis && <button type="button" className="profile-export-button" onClick={() => window.print()} title="В окне печати выберите «Сохранить как PDF»">
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v11m0 0 4-4m-4 4-4-4M5 16v4h14v-4" /></svg>
          Экспорт в PDF
        </button>}
      </div>
      <section className="profile-panel profile-analysis-hero" aria-live="polite">
        <span className="eyebrow">АНАЛИЗ НАВЫКОВ</span>
        {!analysis && !failed && <div className="profile-analysis-wait"><span className="profile-analysis-spinner" aria-hidden="true" /><h1>Готовим отчёт</h1><p>AI‑тренер изучает завершённые раунды, чтобы выделить ваши сильные стороны и точки роста. Можно вернуться позже — отчёт сохранится по этой ссылке.</p></div>}
        {failed && <div className="profile-analysis-wait"><h1>Отчёт пока не готов</h1><p>{error ?? 'Модель не смогла завершить анализ. Ваши раунды сохранены — попробуйте ещё раз.'}</p><button className="profile-analyze-button" onClick={onRetry} disabled={isRetrying}>{isRetrying ? 'Запускаем…' : 'Повторить анализ'}</button></div>}
        {analysis && <><h1>Ваш стиль переговоров</h1><p className="profile-analysis-lead">{analysis.summary}</p><p className="profile-muted">Раундов в анализе: {analysis.rounds_analyzed}. Оценка приблизительная и не заменяет просмотр конкретного диалога.</p><div className="profile-analysis-grid"><div className="profile-analysis-card"><span className="eyebrow">ПОЛУЧАЕТСЯ ХОРОШО</span><h2>Сильные стороны</h2><ul>{analysis.strengths.map((item, index) => <li key={index}>{item}</li>)}</ul></div><div className="profile-analysis-card"><span className="eyebrow">ТОЧКИ РОСТА</span><h2>Что улучшить</h2><ul>{analysis.growth_areas.map((item, index) => <li key={index}>{item}</li>)}</ul></div></div><div className="profile-analysis-next"><span className="eyebrow">СЛЕДУЮЩИЙ ШАГ</span><h2>Попробуйте в следующем раунде</h2><ol>{analysis.next_steps.map((item, index) => <li key={index}>{item}</li>)}</ol></div></>}
      </section>
    </main>
  )
}
