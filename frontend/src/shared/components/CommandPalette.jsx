import { useState, useEffect, useRef, useMemo } from 'react'

const PAGES = [
  { key: 'dashboard', label: { en: 'Dashboard', es: 'Dashboard' }, icon: '\uD83C\uDFE0', path: '/' },
  { key: 'automations', label: { en: 'Automations', es: 'Automatizaciones' }, icon: '\uD83D\uDE80', path: '/automations' },
  { key: 'wizard', label: { en: 'AI Wizard', es: 'Asistente IA' }, icon: '\u2728', path: '/wizard' },
  { key: 'intelligence', label: { en: 'Intelligence Hub', es: 'Hub de Inteligencia' }, icon: '\u26A1', path: '/intelligence' },
  { key: 'integrations', label: { en: 'Integrations', es: 'Integraciones' }, icon: '\uD83D\uDD17', path: '/integrations' },
  { key: 'workflows', label: { en: 'Workflows', es: 'Flujos' }, icon: '\uD83D\uDCC4', path: '/workflows' },
  { key: 'executions', label: { en: 'Executions', es: 'Ejecuciones' }, icon: '\u26A1', path: '/executions' },
  { key: 'agents', label: { en: 'Agents', es: 'Agentes' }, icon: '\uD83E\uDD16', path: '/agents' },
  { key: 'swarms', label: { en: 'Swarms', es: 'Enjambres' }, icon: '\uD83D\uDC1D', path: '/swarms' },
  { key: 'connectors', label: { en: 'Connectors', es: 'Conectores' }, icon: '\uD83D\uDD0C', path: '/connectors' },
  { key: 'audit', label: { en: 'Audit Log', es: 'Auditoria' }, icon: '\uD83D\uDCCB', path: '/audit' },
  { key: 'metrics', label: { en: 'Metrics', es: 'Metricas' }, icon: '\uD83D\uDCCA', path: '/metrics' },
  { key: 'settings', label: { en: 'Settings', es: 'Configuracion' }, icon: '\u2699\uFE0F', path: '/settings' },
]

const RECENTS_KEY = 'nxf_recent_pages'
const MAX_RECENTS = 5

function getRecentPages() {
  try { return JSON.parse(localStorage.getItem(RECENTS_KEY) || '[]') } catch { return [] }
}
function addRecentPage(key) {
  const recents = getRecentPages().filter(k => k !== key)
  recents.unshift(key)
  try { localStorage.setItem(RECENTS_KEY, JSON.stringify(recents.slice(0, MAX_RECENTS))) } catch {}
}

export default function CommandPalette({ onNavigate, lang = 'en' }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const inputRef = useRef(null)

  // Ctrl+K / Cmd+K to open
  useEffect(() => {
    const handleKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen(o => !o)
        setQuery('')
        setSelected(0)
      }
      if (e.key === 'Escape' && open) {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [open])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const filtered = useMemo(() => {
    if (!query.trim()) {
      // Show recents first, then all pages
      const recentKeys = getRecentPages()
      const recents = recentKeys.map(k => PAGES.find(p => p.key === k)).filter(Boolean)
      const rest = PAGES.filter(p => !recentKeys.includes(p.key))
      return [...recents, ...rest]
    }
    const q = query.toLowerCase()
    return PAGES.filter(p =>
      p.label.en.toLowerCase().includes(q) ||
      p.label.es.toLowerCase().includes(q) ||
      p.key.includes(q)
    )
  }, [query])

  useEffect(() => { setSelected(0) }, [query])

  const handleSelect = (page) => {
    setOpen(false)
    setQuery('')
    addRecentPage(page.key)
    onNavigate(page.key)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelected(s => Math.min(s + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelected(s => Math.max(s - 1, 0))
    } else if (e.key === 'Enter' && filtered[selected]) {
      handleSelect(filtered[selected])
    }
  }

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  const bg = isDark ? '#1E1F33' : '#fff'
  const text = isDark ? '#E5E7EB' : '#111827'
  const border = isDark ? 'rgba(255,255,255,0.1)' : '#E5E7EB'
  const hover = isDark ? '#2D2E42' : '#F3F4F6'
  const muted = isDark ? '#6B7280' : '#9CA3AF'

  if (!open) return null

  return (
    <div onClick={() => setOpen(false)} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 300,
      display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: '15vh',
      animation: 'fadeIn 0.1s ease-out',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: bg, borderRadius: 16, width: '100%', maxWidth: 520,
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)', overflow: 'hidden',
        border: `1px solid ${border}`,
      }}>
        <div style={{ padding: '12px 16px', borderBottom: `1px solid ${border}`, display: 'flex', alignItems: 'center', gap: 10 }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={muted} strokeWidth="2" strokeLinecap="round">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={lang === 'es' ? 'Buscar pagina...' : 'Search pages...'}
            style={{
              flex: 1, border: 'none', outline: 'none', fontSize: 15, color: text,
              background: 'transparent',
            }}
          />
          <kbd style={{
            padding: '2px 6px', borderRadius: 4, background: hover,
            fontSize: 11, color: muted, border: `1px solid ${border}`,
          }}>ESC</kbd>
        </div>
        <div style={{ maxHeight: 320, overflowY: 'auto', padding: 4 }}>
          {filtered.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: muted, fontSize: 14 }}>
              {lang === 'es' ? 'Sin resultados' : 'No results'}
            </div>
          ) : (() => {
            const recentKeys = !query.trim() ? getRecentPages() : []
            const recentCount = recentKeys.length
            return filtered.map((page, i) => (
              <div key={page.key}>
                {!query.trim() && i === 0 && recentCount > 0 && (
                  <div style={{ padding: '6px 14px', fontSize: 10, fontWeight: 700, color: muted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {lang === 'es' ? 'Recientes' : 'Recent'}
                  </div>
                )}
                {!query.trim() && i === recentCount && recentCount > 0 && (
                  <div style={{ padding: '6px 14px', fontSize: 10, fontWeight: 700, color: muted, textTransform: 'uppercase', letterSpacing: '0.05em', borderTop: `1px solid ${border}`, marginTop: 4, paddingTop: 10 }}>
                    {lang === 'es' ? 'Todas las paginas' : 'All pages'}
                  </div>
                )}
                <div
                  onClick={() => handleSelect(page)}
                  style={{
                    padding: '10px 14px', borderRadius: 8, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 12,
                    background: i === selected ? hover : 'transparent',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={() => setSelected(i)}
                >
                  <span style={{ fontSize: 18 }}>{page.icon}</span>
                  <span style={{ fontSize: 14, color: text, fontWeight: i === selected ? 600 : 400 }}>
                    {page.label[lang]}
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: '#D1D5DB' }}>{page.path}</span>
                </div>
              </div>
            ))
          })()}
        </div>
      </div>
    </div>
  )
}
