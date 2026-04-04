import { useState, useEffect } from 'react'

const SHORTCUTS = [
  { keys: ['Ctrl', 'K'], desc: { en: 'Search pages', es: 'Buscar paginas' } },
  { keys: ['Ctrl', 'Enter'], desc: { en: 'Run / Submit', es: 'Ejecutar / Enviar' } },
  { keys: ['Esc'], desc: { en: 'Close modal / palette', es: 'Cerrar modal / paleta' } },
  { keys: ['?'], desc: { en: 'Show this help', es: 'Mostrar esta ayuda' } },
]

export default function KeyboardShortcuts({ lang = 'en' }) {
  const [show, setShow] = useState(false)

  useEffect(() => {
    const handler = (e) => {
      if (e.key === '?' && !e.ctrlKey && !e.metaKey && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault()
        setShow(s => !s)
      }
      if (e.key === 'Escape' && show) setShow(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [show])

  if (!show) return null

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  const bg = isDark ? '#1E1F33' : '#fff'
  const text = isDark ? '#E5E7EB' : '#111827'
  const muted = isDark ? '#6B7280' : '#9CA3AF'
  const kbdBg = isDark ? '#2D2E42' : '#F3F4F6'
  const border = isDark ? 'rgba(255,255,255,0.1)' : '#E5E7EB'

  return (
    <div onClick={() => setShow(false)} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 280,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      animation: 'fadeIn 0.15s ease-out',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: bg, borderRadius: 14, padding: 24, maxWidth: 380, width: '100%',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)', border: `1px solid ${border}`,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: text, margin: 0 }}>
            {lang === 'es' ? 'Atajos de Teclado' : 'Keyboard Shortcuts'}
          </h3>
          <button onClick={() => setShow(false)} style={{
            background: kbdBg, border: 'none', borderRadius: 6, width: 28, height: 28,
            cursor: 'pointer', color: muted, fontSize: 14,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>&times;</button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {SHORTCUTS.map((s, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, color: isDark ? '#D1D5DB' : '#374151' }}>
                {s.desc[lang] || s.desc.en}
              </span>
              <div style={{ display: 'flex', gap: 4 }}>
                {s.keys.map((k, j) => (
                  <kbd key={j} style={{
                    padding: '3px 8px', borderRadius: 4, background: kbdBg,
                    border: `1px solid ${border}`, fontSize: 11, fontWeight: 600,
                    color: muted, fontFamily: 'monospace',
                  }}>{k === 'Ctrl' && navigator.platform.includes('Mac') ? '\u2318' : k}</kbd>
                ))}
              </div>
            </div>
          ))}
        </div>

        <p style={{ fontSize: 11, color: muted, marginTop: 16, textAlign: 'center' }}>
          {lang === 'es' ? 'Presiona ? para cerrar' : 'Press ? to close'}
        </p>
      </div>
    </div>
  )
}
