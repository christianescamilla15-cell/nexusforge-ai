/**
 * Returns a human-readable relative time string.
 * timeAgo('2026-04-04T10:00:00Z', 'es') → "hace 2h"
 */
export function timeAgo(dateStr, lang = 'en') {
  if (!dateStr) return ''
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = Math.max(0, now - then)
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (lang === 'es') {
    if (seconds < 60) return 'ahora'
    if (minutes < 60) return `hace ${minutes}m`
    if (hours < 24) return `hace ${hours}h`
    if (days < 7) return `hace ${days}d`
    return new Date(dateStr).toLocaleDateString('es-ES', { month: 'short', day: 'numeric' })
  }

  if (seconds < 60) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
