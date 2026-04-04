import { useState, useEffect } from 'react'
import { fireConfetti } from '../utils/confetti'

const STORAGE_KEY = 'nxf_getting_started'

const STEPS = [
  { key: 'wizard', label: { en: 'Create your first automation with AI Wizard', es: 'Crea tu primera automatizacion con el Wizard IA' }, path: '/wizard' },
  { key: 'integration', label: { en: 'Connect an LLM provider (Groq or Claude)', es: 'Conecta un proveedor LLM (Groq o Claude)' }, path: '/integrations' },
  { key: 'run', label: { en: 'Run an automation and see results', es: 'Ejecuta una automatizacion y ve los resultados' }, path: '/automations' },
  { key: 'intelligence', label: { en: 'Try the Intelligence Hub', es: 'Prueba el Hub de Inteligencia' }, path: '/intelligence' },
]

function getCompleted() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') } catch { return [] }
}

export function markGettingStartedStep(key) {
  const completed = getCompleted()
  if (!completed.includes(key)) {
    completed.push(key)
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(completed)) } catch {}
  }
}

export default function GettingStarted({ lang = 'en', onNavigate }) {
  const [completed, setCompleted] = useState(getCompleted)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    const handler = () => setCompleted(getCompleted())
    window.addEventListener('storage', handler)
    return () => window.removeEventListener('storage', handler)
  }, [])

  const allDone = completed.length >= STEPS.length

  // Celebration when all done
  // Fire confetti once when all done
  const [confettiFired, setConfettiFired] = useState(false)
  useEffect(() => {
    if (allDone && !dismissed && !confettiFired) {
      fireConfetti()
      setConfettiFired(true)
    }
  }, [allDone, dismissed, confettiFired])

  if (allDone && !dismissed) {
    return (
      <div style={{
        background: 'linear-gradient(135deg, rgba(99,102,241,0.08), rgba(16,185,129,0.08))',
        borderRadius: 14, border: '1px solid rgba(99,102,241,0.2)',
        padding: 24, marginBottom: 20, textAlign: 'center',
        animation: 'fadeIn 0.5s ease-out',
      }}>
        <div style={{ fontSize: 48, marginBottom: 8 }}>&#x1F389;</div>
        <h3 style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          {lang === 'es' ? 'Felicidades! Completaste los primeros pasos' : 'Congratulations! You completed Getting Started'}
        </h3>
        <p style={{ fontSize: 13, color: '#6B7280', marginBottom: 12 }}>
          {lang === 'es' ? 'Ya estas listo para automatizar como un pro.' : "You're ready to automate like a pro."}
        </p>
        <button onClick={() => setDismissed(true)} style={{
          padding: '8px 20px', borderRadius: 8, border: 'none',
          background: '#6366F1', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
        }}>{lang === 'es' ? 'Cerrar' : 'Dismiss'}</button>
      </div>
    )
  }

  if (dismissed) return null

  // Don't show if user has >3 automations (not a new user)
  const user = (() => { try { return JSON.parse(localStorage.getItem('nf_user') || '{}') } catch { return {} } })()
  if (user.isGuest) return null

  const progress = Math.round((completed.length / STEPS.length) * 100)

  return (
    <div style={{
      background: '#fff', borderRadius: 14, border: '1px solid #E5E7EB',
      padding: 20, marginBottom: 20, animation: 'fadeIn 0.3s ease-out',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: '#111827', marginBottom: 2 }}>
            {lang === 'es' ? 'Primeros pasos' : 'Getting Started'}
          </h3>
          <span style={{ fontSize: 12, color: '#9CA3AF' }}>
            {completed.length}/{STEPS.length} {lang === 'es' ? 'completados' : 'completed'}
          </span>
        </div>
        <button onClick={() => setDismissed(true)} style={{
          background: 'none', border: 'none', color: '#D1D5DB', cursor: 'pointer', fontSize: 18,
        }}>&times;</button>
      </div>

      {/* Progress bar */}
      <div style={{ height: 4, background: '#E5E7EB', borderRadius: 2, marginBottom: 14 }}>
        <div style={{
          height: '100%', borderRadius: 2, transition: 'width 0.3s',
          background: 'linear-gradient(90deg, #6366F1, #8B5CF6)',
          width: `${progress}%`,
        }} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {STEPS.map(step => {
          const done = completed.includes(step.key)
          return (
            <div key={step.key}
              onClick={() => !done && onNavigate(step.key === 'wizard' ? 'wizard' : step.key === 'integration' ? 'integrations' : step.key === 'run' ? 'automations' : 'intelligence')}
              style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px',
                borderRadius: 8, cursor: done ? 'default' : 'pointer',
                background: done ? '#F0FDF4' : 'transparent',
                border: `1px solid ${done ? '#BBF7D0' : '#F3F4F6'}`,
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => !done && (e.currentTarget.style.background = '#F9FAFB')}
              onMouseLeave={e => !done && (e.currentTarget.style.background = 'transparent')}
            >
              <span style={{
                width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: done ? '#10B981' : '#E5E7EB', color: done ? '#fff' : '#9CA3AF',
                fontSize: 12, fontWeight: 700,
              }}>
                {done ? '\u2713' : completed.length + 1 === STEPS.indexOf(step) + 1 ? '\u2192' : ''}
              </span>
              <span style={{
                fontSize: 13, color: done ? '#166534' : '#374151',
                textDecoration: done ? 'line-through' : 'none',
                fontWeight: done ? 400 : 500,
              }}>
                {step.label[lang]}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
