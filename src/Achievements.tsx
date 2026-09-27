import { achievementCatalog } from './achievementCatalog'

export function Achievements({ unlocked, onlyUnlocked = false, alignWithProfile = false }: { unlocked: string[]; onlyUnlocked?: boolean; alignWithProfile?: boolean }) {
  const unlockedIds = new Set(unlocked)
  const visibleAchievements = onlyUnlocked
    ? achievementCatalog.filter((achievement) => unlockedIds.has(achievement.id))
    : achievementCatalog

  const cards = visibleAchievements.map((achievement) => {
    const isUnlocked = unlockedIds.has(achievement.id)
    const catalogIndex = achievementCatalog.indexOf(achievement)
    return (
      <div className={`achievement-card${isUnlocked ? ' unlocked' : ''}`} key={achievement.id}>
        <span className="achievement-mark" aria-hidden="true">{isUnlocked ? '✓' : String(catalogIndex + 1).padStart(2, '0')}</span>
        <div>
          <strong>{achievement.title}</strong>
          <p>{achievement.description}</p>
          <span className="achievement-state">{isUnlocked ? 'Получено' : 'Пока не открыто'}</span>
        </div>
      </div>
    )
  })

  return (
    <div className={`achievement-grid${alignWithProfile ? ' achievement-grid-profile' : ''}`}>
      {alignWithProfile ? (
        <>
          <div className="achievement-group">{cards.slice(0, 2)}</div>
          <div className="achievement-group">{cards.slice(2)}</div>
        </>
      ) : cards}
    </div>
  )
}
