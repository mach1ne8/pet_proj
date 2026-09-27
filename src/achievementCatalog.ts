export const achievementCatalog = [
  {
    id: 'first_round',
    title: 'Первый шаг',
    description: 'Завершите раунд хотя бы с одной своей репликой.',
  },
  {
    id: 'curious_mind',
    title: 'Сильные вопросы',
    description: 'Задайте вопросы в трёх разных ходах одного раунда.',
  },
  {
    id: 'batna_scout',
    title: 'Искатель альтернатив',
    description: 'Выясните BATNA собеседника вопросом об альтернативах.',
  },
  {
    id: 'independent',
    title: 'Своими силами',
    description: 'Проведите минимум три хода без SOS-подсказок.',
  },
  {
    id: 'trust_builder',
    title: 'Заслуженное доверие',
    description: 'Поднимите доверие на 10 и снизьте риск срыва на 5 пунктов.',
  },
] as const

export const achievementTotal = achievementCatalog.length
