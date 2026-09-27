import { useEffect, useRef } from 'react'

type ScenarioOption = { id: string; name: string }

type Props = {
  scenarios: ScenarioOption[]
  selectedId: string | null
  onSelect: (id: string) => void
  disabled: boolean
}

export function ScenarioPicker({ scenarios, selectedId, onSelect, disabled }: Props) {
  const pickerRef = useRef<HTMLDetailsElement>(null)
  const selected = scenarios.find((item) => item.id === selectedId)

  useEffect(() => {
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (event.target instanceof Node && !pickerRef.current?.contains(event.target)) {
        pickerRef.current?.removeAttribute('open')
      }
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && pickerRef.current?.open) {
        pickerRef.current.open = false
        pickerRef.current.querySelector('summary')?.focus()
      }
    }
    document.addEventListener('pointerdown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [])

  useEffect(() => {
    if (disabled) pickerRef.current?.removeAttribute('open')
  }, [disabled])

  const focusOption = (index: number) => {
    pickerRef.current?.querySelectorAll<HTMLButtonElement>('.scenario-option')[index]?.focus()
  }

  return (
    <div className="scenario-picker-field">
      <span className="scenario-select-label" id="scenario-label">Тема переговоров</span>
      <details className="scenario-picker" ref={pickerRef}>
        <summary
          aria-labelledby="scenario-label scenario-selected"
          aria-disabled={disabled}
          tabIndex={disabled ? -1 : 0}
          onClick={(event) => { if (disabled) event.preventDefault() }}
          onKeyDown={(event) => {
            if (!disabled && event.key === 'ArrowDown') {
              event.preventDefault()
              pickerRef.current!.open = true
              requestAnimationFrame(() => focusOption(0))
            }
          }}
        >
          <span id="scenario-selected">{selected?.name ?? 'Загрузка сценариев…'}</span>
          <svg aria-hidden="true" viewBox="0 0 20 20"><path d="m5 7.5 5 5 5-5" /></svg>
        </summary>
        <div className="scenario-options" role="group" aria-label="Сценарии переговоров">
          {scenarios.map((item, index) => (
            <button
              type="button"
              className={`scenario-option${item.id === selectedId ? ' selected' : ''}`}
              aria-current={item.id === selectedId ? 'true' : undefined}
              key={item.id}
              onClick={() => {
                onSelect(item.id)
                pickerRef.current?.removeAttribute('open')
                pickerRef.current?.querySelector('summary')?.focus()
              }}
              onKeyDown={(event) => {
                if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                  event.preventDefault()
                  focusOption((index + (event.key === 'ArrowDown' ? 1 : -1) + scenarios.length) % scenarios.length)
                } else if (event.key === 'Home' || event.key === 'End') {
                  event.preventDefault()
                  focusOption(event.key === 'Home' ? 0 : scenarios.length - 1)
                }
              }}
            >
              <span>{item.name}</span>
              {item.id === selectedId && <span className="scenario-option-check" aria-hidden="true">✓</span>}
            </button>
          ))}
        </div>
      </details>
    </div>
  )
}
