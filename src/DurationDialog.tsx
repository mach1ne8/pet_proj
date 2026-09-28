import { useEffect, useRef, useState } from 'react'

const durationOptions = [10, 15, 20, 30, 45, 60]

type Props = {
  scenarioName: string
  difficultyLabel: string
  isStarting: boolean
  error: string | null
  onClose: () => void
  onConfirm: (minutes: number) => void
}

export function DurationDialog({ scenarioName, difficultyLabel, isStarting, error, onClose, onConfirm }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [minutes, setMinutes] = useState(10)

  useEffect(() => {
    const dialog = dialogRef.current
    dialog?.showModal()
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      dialog?.close()
      document.body.style.overflow = previousOverflow
    }
  }, [])

  return (
    <dialog
      ref={dialogRef}
      className="duration-dialog"
      aria-labelledby="duration-title"
      aria-describedby="duration-description"
      onCancel={(event) => {
        event.preventDefault()
        if (!isStarting) onClose()
      }}
    >
      <form onSubmit={(event) => { event.preventDefault(); if (!isStarting) onConfirm(minutes) }}>
        <div className="duration-dialog-heading">
          <span className="eyebrow">Настройка раунда</span>
          <button type="button" className="duration-dialog-close" onClick={onClose} disabled={isStarting} aria-label="Закрыть выбор времени">×</button>
        </div>
        <h2 id="duration-title">Сколько времени выделим?</h2>
        <p className="duration-dialog-context">{scenarioName} · {difficultyLabel}</p>
        <div className="duration-options" role="group" aria-label="Продолжительность сессии">
          {durationOptions.map((option) => (
            <button
              key={option}
              type="button"
              className={`duration-option${minutes === option ? ' selected' : ''}`}
              aria-pressed={minutes === option}
              onClick={() => setMinutes(option)}
              disabled={isStarting}
              autoFocus={option === 10}
            >{option === 60 ? '1 час' : `${option} мин`}</button>
          ))}
        </div>
        <p id="duration-description" className="duration-dialog-description">Когда время закончится, покажем итоги. Раунд можно завершить раньше.</p>
        {error && <p className="duration-dialog-error" role="alert">{error}</p>}
        <button type="submit" className="primary-button duration-confirm" disabled={isStarting}>
          {isStarting ? 'Подготавливаем…' : 'Начать раунд'}
        </button>
      </form>
    </dialog>
  )
}
