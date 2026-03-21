export function formatDateTime(value?: string | null) {
  if (!value) return '刚刚'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '刚刚'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function groupConversationLabel(value?: string | null) {
  if (!value) return '更早'
  const date = new Date(value)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = diff / (1000 * 60 * 60 * 24)
  if (days < 1 && now.getDate() === date.getDate()) return '今天'
  if (days < 7) return '最近 7 天'
  return '更早'
}
