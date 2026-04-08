export function formatDate(iso, lang) {
  if (!iso) return '--'
  return new Date(iso).toLocaleString(lang === 'es' ? 'es-ES' : 'en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function formatDateWithSeconds(iso, lang) {
  if (!iso) return '--'
  return new Date(iso).toLocaleString(lang === 'es' ? 'es-ES' : 'en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}
