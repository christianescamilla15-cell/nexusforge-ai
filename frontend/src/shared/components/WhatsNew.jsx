import { useState, useEffect } from 'react'

const CHANGELOG = [
  {
    version: '2.5',
    date: '2026-04-04',
    items: [
      { type: 'new', text: { en: 'Intelligence Hub — Enterprise Ops, Doc Intelligence, and Analyze in one page', es: 'Hub de Inteligencia — Enterprise Ops, Doc Intelligence y Analisis en una pagina' } },
      { type: 'new', text: { en: 'Command Palette (Ctrl+K) — instant navigation to any page', es: 'Paleta de Comandos (Ctrl+K) — navegacion instantanea' } },
      { type: 'new', text: { en: 'System Status page — real-time health of all components', es: 'Pagina de Estado — salud en tiempo real de todos los componentes' } },
      { type: 'new', text: { en: 'Workflow export/import as JSON', es: 'Exportar/importar workflows como JSON' } },
      { type: 'improve', text: { en: '24 AI agents upgraded to superagents with deterministic layers', es: '24 agentes IA upgradeados a superagentes con capas deterministicas' } },
      { type: 'improve', text: { en: 'React Router — URL-based navigation, deep linking, back button works', es: 'React Router — navegacion por URLs, deep linking, boton atras funciona' } },
      { type: 'improve', text: { en: 'Automation search, pagination, edit, and favorites', es: 'Busqueda, paginacion, edicion y favoritos en automatizaciones' } },
      { type: 'improve', text: { en: 'Dashboard auto-refresh every 30s with "updated ago" indicator', es: 'Dashboard auto-refresh cada 30s con indicador de actualizacion' } },
      { type: 'fix', text: { en: 'Redis live on production (Upstash TLS)', es: 'Redis activo en produccion (Upstash TLS)' } },
      { type: 'fix', text: { en: 'API key encryption, CORS hardened, RBAC ownership checks', es: 'Encriptacion de API keys, CORS endurecido, verificacion de propiedad' } },
    ],
  },
]

const LATEST_VERSION = CHANGELOG[0].version
const STORAGE_KEY = 'nxf_whats_new_seen'

const TYPE_BADGE = {
  new: { label: 'NEW', color: '#6366F1', bg: 'rgba(99,102,241,0.1)' },
  improve: { label: 'IMPROVED', color: '#059669', bg: 'rgba(5,150,105,0.1)' },
  fix: { label: 'FIX', color: '#F59E0B', bg: 'rgba(245,158,11,0.1)' },
}

export default function WhatsNew({ lang = 'en' }) {
  const [show, setShow] = useState(false)

  useEffect(() => {
    try {
      const seen = localStorage.getItem(STORAGE_KEY)
      if (seen !== LATEST_VERSION) setShow(true)
    } catch {}
  }, [])

  const dismiss = () => {
    setShow(false)
    try { localStorage.setItem(STORAGE_KEY, LATEST_VERSION) } catch {}
  }

  if (!show) return null

  const entry = CHANGELOG[0]

  return (
    <div onClick={dismiss} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 250,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      animation: 'fadeIn 0.2s ease-out',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#fff', borderRadius: 16, padding: 28, maxWidth: 500,
        width: '100%', boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
        maxHeight: '80vh', overflowY: 'auto',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: '#111827', marginBottom: 2 }}>
              {lang === 'es' ? 'Novedades' : "What's New"}
            </h2>
            <span style={{ fontSize: 12, color: '#9CA3AF' }}>v{entry.version} &middot; {entry.date}</span>
          </div>
          <button onClick={dismiss} style={{
            background: '#F3F4F6', border: 'none', borderRadius: 8,
            width: 32, height: 32, cursor: 'pointer', fontSize: 16, color: '#9CA3AF',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>&times;</button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {entry.items.map((item, i) => {
            const badge = TYPE_BADGE[item.type] || TYPE_BADGE.improve
            return (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <span style={{
                  padding: '2px 6px', borderRadius: 4, fontSize: 9, fontWeight: 700,
                  background: badge.bg, color: badge.color, whiteSpace: 'nowrap', marginTop: 2,
                }}>{badge.label}</span>
                <span style={{ fontSize: 13, color: '#374151', lineHeight: 1.5 }}>
                  {item.text[lang] || item.text.en}
                </span>
              </div>
            )
          })}
        </div>

        <button onClick={dismiss} style={{
          marginTop: 20, width: '100%', padding: '11px 0', borderRadius: 8,
          border: 'none', background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
          color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
        }}>
          {lang === 'es' ? 'Entendido' : 'Got it'}
        </button>
      </div>
    </div>
  )
}
