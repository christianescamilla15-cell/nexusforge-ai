import { useEffect, useState } from 'react'
import { fetchAPI } from '../../services/api'
import { useIsMobile } from '../../shared/hooks/useIsMobile'

/**
 * Tenant Showcase — client-facing demo of the full NexusForge pipeline.
 *
 * Renders the pre-computed showcase report and strangler migration plan
 * for a synthetic tenant. Data is served by the public endpoints:
 *   GET /api/refactor/showcase
 *   GET /api/refactor/showcase/{tenant_id}
 *   GET /api/refactor/showcase/{tenant_id}/strangler/{app_codename}
 *
 * Content is read-only JSON committed to backend/showcase_data/. No
 * live scans run at request time — the dashboard is snappy and the
 * demo reproducible.
 */

const SEVERITY_COLORS = {
  critical: '#DC2626',
  high: '#F59E0B',
  medium: '#3B82F6',
  low: '#9CA3AF',
}

const RISK_COLORS = {
  low: { bg: '#DCFCE7', fg: '#166534', border: '#86EFAC' },
  medium: { bg: '#FEF3C7', fg: '#92400E', border: '#FCD34D' },
  high: { bg: '#FEE2E2', fg: '#991B1B', border: '#FCA5A5' },
}

const CATEGORY_LABELS = {
  sql_injection: 'SQL Injection',
  hardcoded_cred: 'Hardcoded Credentials',
  missing_auth: 'Missing Authorization',
  weak_crypto: 'Weak Cryptography',
  suppressed_exception: 'Suppressed Exceptions',
  command_injection: 'Command Injection',
  pii_leak: 'PII Leak',
  info_leak: 'Information Leak',
}

function KpiCard({ label, value, subtitle, color = '#111827' }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: '16px 20px', minHeight: 96,
    }}>
      <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.3 }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 800, color, marginTop: 6 }}>{value}</div>
      {subtitle && <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4 }}>{subtitle}</div>}
    </div>
  )
}

function SeverityBar({ findingsBySeverity }) {
  const total = Object.values(findingsBySeverity || {}).reduce((a, b) => a + b, 0)
  if (total === 0) return null
  const order = ['critical', 'high', 'medium', 'low']
  return (
    <div style={{ display: 'flex', height: 10, borderRadius: 6, overflow: 'hidden', marginTop: 8 }}>
      {order.map(sev => {
        const count = findingsBySeverity[sev] || 0
        if (count === 0) return null
        const pct = (count / total) * 100
        return (
          <div
            key={sev}
            title={`${sev}: ${count.toLocaleString()}`}
            style={{ width: `${pct}%`, background: SEVERITY_COLORS[sev] }}
          />
        )
      })}
    </div>
  )
}

function AppCard({ app, onSelect, selected }) {
  const bySev = app.findings?.by_severity || {}
  const byCat = app.findings?.by_category || {}
  const total = app.findings?.total || 0
  return (
    <button
      onClick={() => onSelect(app.codename)}
      style={{
        textAlign: 'left', cursor: 'pointer', width: '100%',
        background: selected ? '#EEF2FF' : '#fff',
        border: selected ? '2px solid #6366F1' : '1px solid #E5E7EB',
        borderRadius: 12, padding: '16px 18px',
        transition: 'all 0.15s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: 13, color: '#6B7280', fontWeight: 600 }}>{app.codename}</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginTop: 2 }}>
            {app.label || app.codename}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#DC2626' }}>
            {total.toLocaleString()}
          </div>
          <div style={{ fontSize: 11, color: '#9CA3AF' }}>findings</div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#6B7280', marginTop: 10 }}>
        <span>{app.total_files?.toLocaleString() || 0} files</span>
        <span>•</span>
        <span>{app.total_lines?.toLocaleString() || 0} LOC</span>
        <span>•</span>
        <span>risk {app.risk_score?.toLocaleString() || 0}</span>
      </div>
      <SeverityBar findingsBySeverity={bySev} />
      {Object.keys(byCat).length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
          {Object.entries(byCat).slice(0, 3).map(([cat, n]) => (
            <span key={cat} style={{
              fontSize: 10, padding: '3px 8px', borderRadius: 10,
              background: '#F3F4F6', color: '#374151',
            }}>
              {CATEGORY_LABELS[cat] || cat}: {n}
            </span>
          ))}
        </div>
      )}
    </button>
  )
}

function StranglerPhaseCard({ phase }) {
  const risk = RISK_COLORS[phase.risk] || RISK_COLORS.medium
  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: '18px 20px', marginBottom: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>
            Phase {phase.index}
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginTop: 2 }}>
            {phase.title.replace(/^Phase \d+:\s*/, '')}
          </div>
        </div>
        <div style={{
          padding: '4px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700,
          background: risk.bg, color: risk.fg, border: `1px solid ${risk.border}`,
          textTransform: 'uppercase', letterSpacing: 0.5,
        }}>
          {phase.risk} risk
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#6B7280', marginTop: 10 }}>
        <span><b style={{ color: '#111827' }}>{phase.effort_days}</b> eng-days</span>
        <span>•</span>
        <span><b style={{ color: '#111827' }}>{phase.total_loc?.toLocaleString() || 0}</b> LOC</span>
        <span>•</span>
        <span><b style={{ color: '#DC2626' }}>{phase.total_vulns?.toLocaleString() || 0}</b> vulns</span>
      </div>

      <div style={{ fontSize: 13, color: '#4B5563', marginTop: 12, lineHeight: 1.5 }}>
        {phase.rationale}
      </div>

      <div style={{ marginTop: 12, padding: '10px 12px', background: '#F9FAFB', borderRadius: 8 }}>
        <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, marginBottom: 4 }}>STRATEGY</div>
        <div style={{ fontSize: 12, color: '#374151' }}>{phase.strategy}</div>
      </div>

      <div style={{ marginTop: 8, padding: '10px 12px', background: '#FEF2F2', borderRadius: 8 }}>
        <div style={{ fontSize: 11, color: '#991B1B', fontWeight: 600, marginBottom: 4 }}>ROLLBACK</div>
        <div style={{ fontSize: 12, color: '#7F1D1D' }}>{phase.rollback}</div>
      </div>
    </div>
  )
}

export default function TenantShowcase({ lang = 'en' }) {
  const isMobile = useIsMobile()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [report, setReport] = useState(null)
  const [selectedApp, setSelectedApp] = useState(null)
  const [stranglerPlan, setStranglerPlan] = useState(null)
  const [planLoading, setPlanLoading] = useState(false)

  const tenantId = 'tenant-alpha'

  // Load the main showcase report
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchAPI(`/refactor/showcase/${tenantId}`).then(res => {
      if (cancelled) return
      if (res.error) {
        setError(res.error)
      } else {
        setReport(res.data)
        if (res.data?.apps?.length > 0) {
          setSelectedApp(res.data.apps[0].codename)
        }
      }
      setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  // Load the strangler plan when an app is selected
  useEffect(() => {
    if (!selectedApp) return
    let cancelled = false
    setPlanLoading(true)
    setStranglerPlan(null)
    fetchAPI(`/refactor/showcase/${tenantId}/strangler/${selectedApp}`).then(res => {
      if (cancelled) return
      if (!res.error) setStranglerPlan(res.data)
      setPlanLoading(false)
    })
    return () => { cancelled = true }
  }, [selectedApp])

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#6B7280' }}>
        {lang === 'es' ? 'Cargando datos del showcase...' : 'Loading showcase data...'}
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <div style={{ color: '#DC2626', fontWeight: 600, marginBottom: 8 }}>
          {lang === 'es' ? 'Error al cargar' : 'Failed to load'}
        </div>
        <div style={{ color: '#6B7280', fontSize: 13 }}>{error}</div>
      </div>
    )
  }

  if (!report) return null

  const totals = report.totals || {}
  const durationSec = ((report.duration_ms || 0) / 1000).toFixed(2)
  const totalEffortDays = stranglerPlan?.total_effort_days || 0

  return (
    <div style={{ padding: isMobile ? 16 : 32, maxWidth: 1400, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 12, color: '#6366F1', fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase' }}>
          NexusForge Showcase
        </div>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: '#111827', margin: '6px 0 4px' }}>
          {lang === 'es' ? 'Modernización de Sistemas Legacy' : 'Legacy System Modernization'}
        </h1>
        <p style={{ fontSize: 14, color: '#6B7280', maxWidth: 800 }}>
          {lang === 'es'
            ? 'Cinco aplicaciones legacy ingestadas, analizadas y con plan de migración completo — en segundos.'
            : 'Five legacy applications ingested, analyzed and mapped to a complete migration plan — in seconds.'}
        </p>
      </div>

      {/* Hero stat band */}
      <div style={{
        background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
        borderRadius: 16, padding: isMobile ? '20px 20px' : '28px 32px',
        color: '#fff', marginBottom: 24,
      }}>
        <div style={{ fontSize: 13, opacity: 0.9, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
          {lang === 'es' ? 'Pipeline end-to-end' : 'End-to-end pipeline'}
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
          gap: 20, marginTop: 16,
        }}>
          <div>
            <div style={{ fontSize: 32, fontWeight: 800 }}>{totals.apps || 0}</div>
            <div style={{ fontSize: 12, opacity: 0.85 }}>{lang === 'es' ? 'Aplicaciones' : 'Applications'}</div>
          </div>
          <div>
            <div style={{ fontSize: 32, fontWeight: 800 }}>{(totals.lines_of_code || 0).toLocaleString()}</div>
            <div style={{ fontSize: 12, opacity: 0.85 }}>{lang === 'es' ? 'Líneas de código' : 'Lines of code'}</div>
          </div>
          <div>
            <div style={{ fontSize: 32, fontWeight: 800 }}>{(totals.findings || 0).toLocaleString()}</div>
            <div style={{ fontSize: 12, opacity: 0.85 }}>{lang === 'es' ? 'Hallazgos' : 'Findings'}</div>
          </div>
          <div>
            <div style={{ fontSize: 32, fontWeight: 800 }}>{durationSec}s</div>
            <div style={{ fontSize: 12, opacity: 0.85 }}>{lang === 'es' ? 'Duración pipeline' : 'Pipeline duration'}</div>
          </div>
        </div>
      </div>

      {/* Totals KPIs */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
        gap: 12, marginBottom: 24,
      }}>
        <KpiCard
          label={lang === 'es' ? 'Archivos ingestados' : 'Files ingested'}
          value={(totals.files || 0).toLocaleString()}
          color="#111827"
        />
        <KpiCard
          label={lang === 'es' ? 'Críticos' : 'Critical'}
          value={(totals.findings_by_severity?.critical || 0).toLocaleString()}
          subtitle={lang === 'es' ? 'severidad crítica' : 'critical severity'}
          color="#DC2626"
        />
        <KpiCard
          label={lang === 'es' ? 'Riesgo ponderado' : 'Weighted risk'}
          value={(totals.risk_score || 0).toLocaleString()}
          color="#F59E0B"
        />
        <KpiCard
          label={lang === 'es' ? 'Total hallazgos' : 'Total findings'}
          value={(totals.findings || 0).toLocaleString()}
          color="#6366F1"
        />
      </div>

      {/* Findings by category */}
      {totals.findings_by_category && (
        <div style={{
          background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
          padding: '20px 24px', marginBottom: 24,
        }}>
          <div style={{ fontSize: 13, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 12 }}>
            {lang === 'es' ? 'Hallazgos por categoría' : 'Findings by category'}
          </div>
          {Object.entries(totals.findings_by_category)
            .sort((a, b) => b[1] - a[1])
            .map(([cat, count]) => {
              const pct = (count / totals.findings) * 100
              return (
                <div key={cat} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                    <span style={{ color: '#374151', fontWeight: 600 }}>{CATEGORY_LABELS[cat] || cat}</span>
                    <span style={{ color: '#6B7280' }}>{count.toLocaleString()} ({pct.toFixed(1)}%)</span>
                  </div>
                  <div style={{ height: 6, background: '#F3F4F6', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{
                      width: `${pct}%`, height: '100%',
                      background: 'linear-gradient(90deg, #6366F1, #8B5CF6)',
                    }} />
                  </div>
                </div>
              )
            })}
        </div>
      )}

      {/* App grid + strangler detail */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : '380px 1fr',
        gap: 16, marginBottom: 24,
      }}>
        {/* Left: app list */}
        <div>
          <div style={{ fontSize: 13, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 10 }}>
            {lang === 'es' ? 'Aplicaciones' : 'Applications'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {(report.apps || []).map(app => (
              <AppCard
                key={app.codename}
                app={app}
                onSelect={setSelectedApp}
                selected={selectedApp === app.codename}
              />
            ))}
          </div>
        </div>

        {/* Right: strangler plan for selected app */}
        <div>
          <div style={{ fontSize: 13, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 10 }}>
            {lang === 'es' ? 'Plan de migración strangler' : 'Strangler migration plan'} — <span style={{ color: '#6366F1' }}>{selectedApp || '...'}</span>
          </div>

          {planLoading && (
            <div style={{ padding: 24, textAlign: 'center', color: '#9CA3AF' }}>
              {lang === 'es' ? 'Cargando plan...' : 'Loading plan...'}
            </div>
          )}

          {stranglerPlan && !planLoading && (
            <>
              <div style={{
                background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
                padding: '16px 20px', marginBottom: 12,
              }}>
                <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                  <div>
                    <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>
                      {lang === 'es' ? 'Fases' : 'Phases'}
                    </div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: '#111827' }}>
                      {stranglerPlan.phases?.length || 0}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>
                      {lang === 'es' ? 'Esfuerzo' : 'Effort'}
                    </div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: '#111827' }}>
                      {totalEffortDays}d
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>
                      {lang === 'es' ? 'Módulos' : 'Modules'}
                    </div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: '#111827' }}>
                      {stranglerPlan.total_modules || 0}
                    </div>
                  </div>
                </div>
                {stranglerPlan.narrative && (
                  <div style={{ fontSize: 13, color: '#4B5563', marginTop: 14, lineHeight: 1.5 }}>
                    {stranglerPlan.narrative}
                  </div>
                )}
              </div>

              {(stranglerPlan.phases || []).map(phase => (
                <StranglerPhaseCard key={phase.index} phase={phase} />
              ))}
            </>
          )}
        </div>
      </div>

      {/* Narrative footer */}
      <div style={{
        background: '#0F172A', borderRadius: 12, padding: isMobile ? 20 : 28,
        color: '#E2E8F0', textAlign: 'center',
      }}>
        <div style={{ fontSize: 13, color: '#A78BFA', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1 }}>
          {lang === 'es' ? 'La propuesta de valor' : 'The value prop'}
        </div>
        <div style={{ fontSize: isMobile ? 18 : 22, fontWeight: 700, marginTop: 10, lineHeight: 1.4 }}>
          {lang === 'es'
            ? <>Evaluación manual: <span style={{ color: '#F87171' }}>meses</span>. Con NexusForge: <span style={{ color: '#34D399' }}>segundos</span>.</>
            : <>Manual discovery: <span style={{ color: '#F87171' }}>months</span>. With NexusForge: <span style={{ color: '#34D399' }}>seconds</span>.</>
          }
        </div>
      </div>

    </div>
  )
}
