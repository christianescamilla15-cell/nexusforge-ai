import { useState, useEffect } from 'react'
import { t } from '../../shared/i18n/translations'
import { fetchAPI } from '../../services/api'
import KPICard from './KPICard'
import RecentRuns from './RecentRuns'
import AgentActivity from './AgentActivity'

// Color palette for agent activity bars
const AGENT_COLORS = [
  { color: '#2563EB', colorEnd: '#60A5FA' },
  { color: '#059669', colorEnd: '#34D399' },
  { color: '#D97706', colorEnd: '#FBBF24' },
  { color: '#DC2626', colorEnd: '#F87171' },
  { color: '#0891B2', colorEnd: '#22D3EE' },
  { color: '#7C3AED', colorEnd: '#A78BFA' },
  { color: '#DB2777', colorEnd: '#F472B6' },
]

const PLAN_LIMITS = { free: 5, trial: 10, pro: 100, team: 500, enterprise: -1 }

function PlanUsageBar({ lang, totalRuns }) {
  const user = (() => { try { return JSON.parse(localStorage.getItem('nf_user') || '{}') } catch { return {} } })()
  const plan = user.plan || 'free'
  const limit = PLAN_LIMITS[plan] || 5
  if (limit === -1) return null // enterprise = unlimited

  const pct = Math.min(100, Math.round((totalRuns / limit) * 100))
  const isNear = pct >= 80
  const barColor = isNear ? '#EF4444' : '#6366F1'

  return (
    <div style={{
      padding: '10px 16px', borderRadius: 10, marginBottom: 16,
      background: isNear ? 'rgba(239,68,68,0.05)' : 'rgba(99,102,241,0.04)',
      border: `1px solid ${isNear ? 'rgba(239,68,68,0.2)' : 'rgba(99,102,241,0.15)'}`,
      display: 'flex', alignItems: 'center', gap: 12, fontSize: 13,
    }}>
      <span style={{ color: '#6B7280', whiteSpace: 'nowrap' }}>
        {lang === 'es' ? 'Plan' : 'Plan'}: <strong style={{ color: '#111827', textTransform: 'capitalize' }}>{plan}</strong>
      </span>
      <div style={{ flex: 1, height: 6, background: '#E5E7EB', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ height: '100%', borderRadius: 3, background: barColor, width: `${pct}%`, transition: 'width 0.3s' }} />
      </div>
      <span style={{ color: isNear ? '#EF4444' : '#9CA3AF', whiteSpace: 'nowrap', fontSize: 12 }}>
        {totalRuns}/{limit} {lang === 'es' ? 'ejecuciones' : 'runs'}
      </span>
    </div>
  )
}

function KPIIcon({ type }) {
  const paths = {
    workflows: 'M4 6h16M4 12h8m-8 6h16',
    runs: 'M13 10V3L4 14h7v7l9-11h-7z',
    agents: 'M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5',
    docs: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
  }
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d={paths[type]} />
    </svg>
  )
}

// ── Try It Now Section ──────────────────────────────────────────────────────

function TryItNowSection({ lang = 'en', isMobile, onNavigate }) {
  const [tryText, setTryText] = useState('')
  const [trying, setTrying] = useState(false)
  const [tryResult, setTryResult] = useState(null)
  const [tryDuration, setTryDuration] = useState(0)

  const handleTryAnalyze = async () => {
    if (trying || !tryText.trim()) return
    setTrying(true)
    setTryResult(null)
    const start = Date.now()
    const res = await fetchAPI('/demo/analyze', {
      method: 'POST',
      body: JSON.stringify({ text: tryText }),
    })
    setTryDuration(Date.now() - start)
    setTrying(false)
    if (!res.error && res.data) {
      setTryResult({
        classification: res.data.intent || res.data.classification,
        urgency: res.data.urgency || 'low',
        entities: res.data.entities || [],
        summary: res.data.summary || '',
        suggested_response: res.data.suggested_response || res.data.summary || '',
      })
    }
  }

  const SAMPLE_DATA = [
    {
      label: '\uD83C\uDFAB Ticket',
      text: 'Mi pedido #12345 no ha llegado. Lo compr\u00E9 hace 2 semanas y el tracking muestra que est\u00E1 en la bodega desde el d\u00EDa 5. Necesito una soluci\u00F3n urgente porque es un regalo de cumplea\u00F1os.',
    },
    {
      label: '\uD83D\uDCE7 Email',
      text: 'Hola equipo, necesito reprogramar la reuni\u00F3n del viernes a las 10am. Tambi\u00E9n quiero confirmar si mi contrato incluye soporte premium y cu\u00E1ntas licencias adicionales puedo agregar.',
    },
    {
      label: '\uD83E\uDDFE Factura',
      text: 'FACTURA #2024-0892\nProveedor: Acme Corp\nFecha: 15/03/2026\nConcepto: Servicios de consultor\u00EDa\nSubtotal: $4,500.00\nIVA 16%: $720.00\nTotal: $5,220.00\nCondiciones: Pago a 30 d\u00EDas',
    },
  ]

  return (
    <div style={{
      background: '#fff', borderRadius: 16, border: '1px solid #E5E7EB',
      padding: 24, marginBottom: 24,
    }}>
      <h3 style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
        {lang === 'es' ? '\u26A1 Prueba la IA ahora' : '\u26A1 Try AI Now'}
      </h3>
      <p style={{ fontSize: 13, color: '#9CA3AF', marginBottom: 16 }}>
        {lang === 'es'
          ? 'Pega cualquier texto y ve c\u00F3mo la IA lo analiza en segundos. Sin configurar nada.'
          : 'Paste any text and see AI analyze it in seconds. No setup needed.'}
      </p>

      <div style={{ display: 'flex', gap: 16, flexDirection: isMobile ? 'column' : 'row' }}>
        {/* Input side */}
        <div style={{ flex: 1 }}>
          <textarea
            value={tryText}
            onChange={e => setTryText(e.target.value)}
            placeholder={lang === 'es'
              ? 'Pega un ticket de soporte, email, factura, o cualquier texto...'
              : 'Paste a support ticket, email, invoice, or any text...'}
            rows={5}
            style={{
              width: '100%', padding: 12, borderRadius: 10,
              border: '1px solid #E5E7EB', fontSize: 14, resize: 'vertical',
              boxSizing: 'border-box', fontFamily: 'inherit',
            }}
          />
          <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
            <button
              onClick={handleTryAnalyze}
              disabled={trying || !tryText.trim()}
              style={{
                padding: '10px 20px', borderRadius: 8, border: 'none',
                background: trying || !tryText.trim() ? '#C7D2FE' : '#6366F1',
                color: '#fff', fontWeight: 600, cursor: trying || !tryText.trim() ? 'not-allowed' : 'pointer',
                fontSize: 14, transition: 'background 0.2s',
              }}
            >
              {trying
                ? (lang === 'es' ? 'Analizando...' : 'Analyzing...')
                : (lang === 'es' ? '\uD83D\uDD0D Analizar' : '\uD83D\uDD0D Analyze')}
            </button>
            {SAMPLE_DATA.map(s => (
              <button
                key={s.label}
                onClick={() => setTryText(s.text)}
                style={{
                  padding: '8px 12px', borderRadius: 6, border: '1px solid #E5E7EB',
                  background: '#F9FAFB', fontSize: 12, cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#6366F1'; e.currentTarget.style.background = '#EEF2FF' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.background = '#F9FAFB' }}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Results side */}
        {tryResult && (
          <div style={{
            flex: 1, background: '#F0FDF4', borderRadius: 10, padding: 16,
            border: '1px solid rgba(16,185,129,0.2)',
          }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#059669', marginBottom: 8 }}>
              {lang === 'es' ? '\u2705 An\u00E1lisis completado' : '\u2705 Analysis complete'}
              <span style={{ float: 'right', color: '#9CA3AF', fontWeight: 400 }}>{tryDuration}ms</span>
            </div>
            {tryResult.classification && (
              <div style={{ marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: '#6B7280' }}>
                  {lang === 'es' ? 'Clasificaci\u00F3n:' : 'Classification:'}
                </span>
                <span style={{
                  marginLeft: 8, padding: '2px 8px', borderRadius: 4,
                  background: '#E0E7FF', color: '#4338CA', fontSize: 12, fontWeight: 600,
                }}>
                  {tryResult.classification}
                </span>
              </div>
            )}
            {tryResult.urgency && (
              <div style={{ marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: '#6B7280' }}>
                  {lang === 'es' ? 'Urgencia:' : 'Urgency:'}
                </span>
                <span style={{
                  marginLeft: 8, padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600,
                  background: tryResult.urgency === 'high' ? '#FEE2E2' : tryResult.urgency === 'medium' ? '#FEF3C7' : '#D1FAE5',
                  color: tryResult.urgency === 'high' ? '#DC2626' : tryResult.urgency === 'medium' ? '#D97706' : '#059669',
                }}>
                  {tryResult.urgency}
                </span>
              </div>
            )}
            {tryResult.entities && tryResult.entities.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: '#6B7280' }}>
                  {lang === 'es' ? 'Entidades:' : 'Entities:'}
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                  {tryResult.entities.map((e, i) => (
                    <span key={i} style={{
                      padding: '2px 8px', borderRadius: 4, background: '#F3F4F6',
                      fontSize: 11, color: '#374151',
                    }}>{e}</span>
                  ))}
                </div>
              </div>
            )}
            {tryResult.summary && (
              <div style={{ marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: '#6B7280' }}>
                  {lang === 'es' ? 'Resumen:' : 'Summary:'}
                </span>
                <p style={{ fontSize: 13, color: '#374151', margin: '4px 0 0', lineHeight: 1.5 }}>
                  {tryResult.summary}
                </p>
              </div>
            )}
            {tryResult.suggested_response && (
              <div>
                <span style={{ fontSize: 11, color: '#6B7280' }}>
                  {lang === 'es' ? 'Respuesta sugerida:' : 'Suggested response:'}
                </span>
                <p style={{ fontSize: 13, color: '#374151', margin: '4px 0 0', lineHeight: 1.5, fontStyle: 'italic' }}>
                  {tryResult.suggested_response}
                </p>
              </div>
            )}
            <button
              onClick={() => onNavigate && onNavigate('wizard')}
              style={{
                marginTop: 12, padding: '8px 16px', borderRadius: 8,
                border: 'none', background: '#6366F1', color: '#fff',
                fontSize: 13, fontWeight: 600, cursor: 'pointer',
                transition: 'background 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#4F46E5'}
              onMouseLeave={e => e.currentTarget.style.background = '#6366F1'}
            >
              {lang === 'es' ? '\u2192 Crear automatizaci\u00F3n con esto' : '\u2192 Create automation from this'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Pending Approvals Section ───────────────────────────────────────────────

function PendingApprovalsSection({ lang = 'en' }) {
  const [approvals, setApprovals] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAPI('/results/pending-approvals').then(res => {
      if (!res.error && res.data?.items) {
        setApprovals(res.data.items)
      }
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const handleAction = async (resultId, action) => {
    const res = await fetchAPI(`/results/${resultId}/approval`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!res.error) {
      setApprovals(prev => prev.filter(a => a.id !== resultId))
    }
  }

  if (loading || approvals.length === 0) return null

  return (
    <div style={{
      background: '#FFFBEB', borderRadius: 16, border: '1px solid #FDE68A',
      padding: 20, marginBottom: 24,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
        <span style={{
          width: 8, height: 8, borderRadius: '50%', background: '#F59E0B',
          animation: 'pulse 2s infinite',
        }} />
        <h3 style={{ fontSize: 15, fontWeight: 700, color: '#92400E', margin: 0 }}>
          {lang === 'es'
            ? `Pendientes de aprobaci\u00F3n (${approvals.length})`
            : `Pending approval (${approvals.length})`}
        </h3>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {approvals.map(item => {
          const outputText = item.output_data?.response_message
            || item.output_data?.summary
            || JSON.stringify(item.output_data).slice(0, 200)
          return (
            <div key={item.id} style={{
              padding: 14, borderRadius: 10, background: '#fff',
              border: '1px solid #FDE68A',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 18 }}>{item.automation_icon || '\u26A1'}</span>
                <strong style={{ fontSize: 13, color: '#111827' }}>{item.automation_name}</strong>
                <span style={{
                  marginLeft: 'auto', fontSize: 11, color: '#9CA3AF',
                }}>
                  {item.created_at ? new Date(item.created_at).toLocaleString() : ''}
                </span>
              </div>
              <p style={{
                fontSize: 13, color: '#374151', margin: '0 0 10px', lineHeight: 1.5,
                maxHeight: 60, overflow: 'hidden',
              }}>
                {outputText}
              </p>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={() => handleAction(item.id, 'approved')}
                  style={{
                    padding: '6px 16px', borderRadius: 6, border: 'none',
                    background: '#059669', color: '#fff', fontSize: 12,
                    fontWeight: 600, cursor: 'pointer',
                  }}
                >
                  {lang === 'es' ? '\u2705 Aprobar y enviar' : '\u2705 Approve & send'}
                </button>
                <button
                  onClick={() => handleAction(item.id, 'rejected')}
                  style={{
                    padding: '6px 16px', borderRadius: 6, border: '1px solid #FCA5A5',
                    background: '#FEF2F2', color: '#DC2626', fontSize: 12,
                    fontWeight: 600, cursor: 'pointer',
                  }}
                >
                  {lang === 'es' ? '\u274C Rechazar' : '\u274C Reject'}
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Main Dashboard ──────────────────────────────────────────────────────────

export default function DashboardPage({ lang = 'en', onNavigate }) {
  const [isMobile, setIsMobile] = useState(false)
  const [runs, setRuns] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isDemo, setIsDemo] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const loadDashboard = () => {
    Promise.all([
      fetchAPI('/runs/'),
      fetchAPI('/runs/reliability/health'),
    ]).then(([runsResult, healthResult]) => {
      if (runsResult.error || healthResult.error) {
        setError(runsResult.error || healthResult.error)
        setLoading(false)
        return
      }
      setRuns(runsResult.data?.runs || [])
      setHealth(healthResult.data)
      setIsDemo(runsResult.isDemo || healthResult.isDemo)
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  const [lastRefresh, setLastRefresh] = useState(null)
  const [refreshAgo, setRefreshAgo] = useState('')

  const wrappedLoad = () => {
    loadDashboard()
    setLastRefresh(Date.now())
  }

  useEffect(() => { wrappedLoad() }, [])

  // Update "ago" label every 5s
  useEffect(() => {
    const tick = setInterval(() => {
      if (lastRefresh) {
        const secs = Math.round((Date.now() - lastRefresh) / 1000)
        if (secs < 5) setRefreshAgo(lang === 'es' ? 'ahora' : 'just now')
        else if (secs < 60) setRefreshAgo(lang === 'es' ? `hace ${secs}s` : `${secs}s ago`)
        else setRefreshAgo(lang === 'es' ? `hace ${Math.floor(secs / 60)}m` : `${Math.floor(secs / 60)}m ago`)
      }
    }, 5000)
    return () => clearInterval(tick)
  }, [lastRefresh, lang])

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(wrappedLoad, 30000)
    return () => clearInterval(interval)
  }, [])

  // Map health data to KPI values
  const kpis = health
    ? {
        totalRuns: health.total_runs ?? 0,
        successRate: health.system_success_rate != null
          ? `${(health.system_success_rate * 100).toFixed(1)}%`
          : '\u2014',
        agentsTracked: health.total_agents_tracked ?? 0,
        failedRuns: health.failed_runs ?? 0,
      }
    : { totalRuns: 0, successRate: '\u2014', agentsTracked: 0, failedRuns: 0 }

  // Map health.agents to the shape AgentActivity expects
  const agents = (health?.agents || []).map((a, i) => ({
    name: a.agent,
    count: a.executions,
    ...AGENT_COLORS[i % AGENT_COLORS.length],
  }))

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
        <span style={{ fontSize: 14, color: '#9CA3AF' }}>Loading dashboard...</span>
      </div>
    )
  }

  const hasData = (runs.length > 0) || (health && (health.total_runs > 0 || health.total_agents_tracked > 0))

  const primaryButtonStyle = {
    padding: '12px 28px', borderRadius: 10, border: 'none',
    background: 'linear-gradient(135deg, #6366F1, #818CF8)',
    color: '#fff', fontSize: 15, fontWeight: 700,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
    boxShadow: '0 4px 14px rgba(99,102,241,0.3)',
    transition: 'all 0.2s',
  }
  const secondaryButtonStyle = {
    padding: '12px 28px', borderRadius: 10, border: '2px solid #E5E7EB',
    background: '#fff', color: '#374151', fontSize: 15, fontWeight: 600,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
    transition: 'all 0.2s',
  }
  const quickCardStyle = {
    padding: '20px 16px', borderRadius: 14, border: '1px solid #E5E7EB',
    background: '#fff', cursor: 'pointer', textAlign: 'center',
    transition: 'all 0.2s',
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 24, flexWrap: 'wrap', gap: 8,
      }}>
        <div>
          <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827' }}>
            {t('dashboard', lang)}
          </h1>
          <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF', marginTop: 4 }}>
            {t('dashboardSubtitle', lang)}
            {refreshAgo && (
              <span style={{ marginLeft: 8, fontSize: 11, color: '#D1D5DB' }}>
                &bull; {lang === 'es' ? 'Actualizado' : 'Updated'} {refreshAgo}
              </span>
            )}
          </p>
        </div>
        {isDemo && (
          <span style={{
            padding: '4px 12px', borderRadius: 6, fontSize: 12,
            background: 'rgba(245,158,11,0.08)', color: '#D97706',
            border: '1px solid rgba(245,158,11,0.2)',
            fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#D97706' }} />
            {lang === 'es' ? 'Modo Demo' : 'Demo Mode'}
          </span>
        )}
      </div>

      {/* Error banner for Real mode failures */}
      {error && (
        <div style={{
          padding: '14px 18px', borderRadius: 10, marginBottom: 20,
          background: 'rgba(220,38,38,0.06)', border: '1px solid rgba(220,38,38,0.2)',
          color: '#991B1B', fontSize: 14, lineHeight: 1.6,
          display: 'flex', alignItems: 'flex-start', gap: 10,
        }}>
          <span style={{ flexShrink: 0, fontSize: 16 }}>{'❌'}</span>
          <div>
            <strong>Error:</strong> {error}
          </div>
        </div>
      )}

      {/* Try It Now — always visible for ALL users */}
      <TryItNowSection lang={lang} isMobile={isMobile} onNavigate={onNavigate} />

      {/* Pending Approvals — human-in-the-loop */}
      <PendingApprovalsSection lang={lang} />

      {/* Empty state — shown when no data */}
      {!hasData && !isDemo && !error && (
        <div style={{
          textAlign: 'center', padding: isMobile ? '40px 16px' : '60px 20px',
          background: '#fff', borderRadius: 20, border: '1px solid #E5E7EB',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        }}>
          <span style={{ fontSize: 64, display: 'block', marginBottom: 16 }}>{'\uD83D\uDE80'}</span>
          <h2 style={{ fontSize: isMobile ? 22 : 28, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
            {lang === 'es' ? '!Bienvenido a NexusForge!' : 'Welcome to NexusForge!'}
          </h2>
          <p style={{ fontSize: 16, color: '#6B7280', marginBottom: 0, maxWidth: 500, margin: '0 auto', lineHeight: 1.6 }}>
            {lang === 'es'
              ? 'Crea tu primera automatizacion en menos de 1 minuto'
              : 'Create your first automation in less than 1 minute'}
          </p>
          <p style={{
            fontSize: 13, color: '#818CF8', marginTop: 12,
            fontWeight: 600, letterSpacing: '0.01em',
          }}>
            {lang === 'es'
              ? '5 triggers \u00D7 15 transforms \u00D7 6 actions = 450+ automaciones posibles'
              : '5 triggers \u00D7 15 transforms \u00D7 6 actions = 450+ possible automations'}
          </p>

          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', marginTop: 32, flexWrap: 'wrap' }}>
            <button
              onClick={() => onNavigate && onNavigate('wizard')}
              style={primaryButtonStyle}
              onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-1px)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'none'}
            >
              {'\u2728'} {lang === 'es' ? 'Crear con AI Wizard' : 'Create with AI Wizard'}
            </button>
            <button
              onClick={() => onNavigate && onNavigate('automations')}
              style={secondaryButtonStyle}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#6366F1'; e.currentTarget.style.color = '#6366F1' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.color = '#374151' }}
            >
              {'\uD83D\uDCCB'} {lang === 'es' ? 'Usar una plantilla' : 'Use a template'}
            </button>
          </div>

          {/* Quick-select cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 12, marginTop: 40, maxWidth: 800, margin: '40px auto 0',
          }}>
            {[
              { icon: '\uD83C\uDFAB', title: 'Ticket Triage', desc: lang === 'es' ? 'Clasificar tickets por urgencia' : 'Classify tickets by urgency' },
              { icon: '\uD83D\uDCC4', title: 'Document Analyzer', desc: lang === 'es' ? 'Extraer datos de PDFs' : 'Extract data from PDFs' },
              { icon: '\uD83D\uDCE7', title: 'Email Responder', desc: lang === 'es' ? 'Responder emails automaticamente' : 'Auto-respond to emails' },
              { icon: '\uD83D\uDCCA', title: 'Report Generator', desc: lang === 'es' ? 'Generar reportes ejecutivos' : 'Generate executive reports' },
            ].map(card => (
              <div
                key={card.title}
                onClick={() => onNavigate && onNavigate('wizard')}
                style={quickCardStyle}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#6366F1'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(99,102,241,0.1)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.boxShadow = 'none' }}
              >
                <span style={{ fontSize: 32, display: 'block', marginBottom: 8 }}>{card.icon}</span>
                <strong style={{ fontSize: 14, color: '#111827', display: 'block', marginBottom: 4 }}>{card.title}</strong>
                <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0, lineHeight: 1.4 }}>{card.desc}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KPI Cards — only when there IS data */}
      {(hasData || isDemo) && (
        <>
          <div className="nxf-kpi-grid" data-tour="dashboard-kpis" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(min(200px, 100%), 1fr))',
            gap: 16,
            marginBottom: 24,
          }}>
            <KPICard
              icon={<KPIIcon type="runs" />}
              value={kpis.totalRuns}
              label={lang === 'es' ? 'Ejecuciones Totales' : 'Total Runs'}
            />
            <KPICard
              icon={<KPIIcon type="workflows" />}
              value={kpis.successRate}
              label={lang === 'es' ? 'Tasa de Exito' : 'Success Rate'}
            />
            <KPICard
              icon={<KPIIcon type="agents" />}
              value={kpis.agentsTracked}
              label={lang === 'es' ? 'Agentes Rastreados' : 'Agents Tracked'}
            />
            <KPICard
              icon={<KPIIcon type="docs" />}
              value={kpis.failedRuns}
              label={lang === 'es' ? 'Ejecuciones Fallidas' : 'Failed Runs'}
            />
          </div>

          {/* Plan usage bar */}
          <PlanUsageBar lang={lang} totalRuns={kpis.totalRuns} />

          {/* Quick Actions */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
            gap: 10, marginBottom: 20,
          }}>
            {[
              { key: 'wizard', icon: '\u2728', label: lang === 'es' ? 'Crear Automatizacion' : 'Create Automation', color: '#6366F1' },
              { key: 'intelligence', icon: '\u26A1', label: lang === 'es' ? 'Analizar Documento' : 'Analyze Document', color: '#059669' },
              { key: 'automations', icon: '\u25B6', label: lang === 'es' ? 'Mis Automatizaciones' : 'My Automations', color: '#D97706' },
              { key: 'agents', icon: '\uD83E\uDD16', label: lang === 'es' ? 'Ver Agentes' : 'View Agents', color: '#8B5CF6' },
            ].map(action => (
              <button key={action.key} onClick={() => onNavigate(action.key)} style={{
                padding: '14px 12px', borderRadius: 10,
                border: '1px solid #E5E7EB', background: '#fff',
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10,
                transition: 'all 0.15s', fontSize: 13, fontWeight: 600, color: '#374151',
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = action.color; e.currentTarget.style.background = `${action.color}06` }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.background = '#fff' }}
              >
                <span style={{
                  width: 32, height: 32, borderRadius: 8, background: `${action.color}12`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, flexShrink: 0,
                }}>{action.icon}</span>
                <span style={{ lineHeight: 1.3 }}>{action.label}</span>
              </button>
            ))}
          </div>

          {/* Main content grid */}
          <div className="nxf-two-col-grid" style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : '1fr 380px',
            gap: 16,
            alignItems: 'start',
          }}>
            {/* Recent runs */}
            <div style={{ overflowX: 'auto' }}>
              <RecentRuns runs={runs} />
            </div>

            {/* Right sidebar */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <AgentActivity agents={agents} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
