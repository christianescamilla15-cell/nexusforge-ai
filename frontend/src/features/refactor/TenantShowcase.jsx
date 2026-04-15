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

function AppCard({ app, onSelect, selected, lang }) {
  const [hovered, setHovered] = useState(false)
  const bySev = app.findings?.by_severity || {}
  const byCat = app.findings?.by_category || {}
  const total = app.findings?.total || 0
  const effortDays = app.total_effort_days || 0
  return (
    <button
      onClick={() => onSelect(app.codename)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        textAlign: 'left', cursor: 'pointer', width: '100%',
        background: selected ? '#EEF2FF' : '#fff',
        border: selected ? '2px solid #6366F1' : `1px solid ${hovered ? '#A5B4FC' : '#E5E7EB'}`,
        borderRadius: 12, padding: '16px 18px',
        transform: hovered && !selected ? 'translateY(-1px)' : 'translateY(0)',
        boxShadow: hovered && !selected ? '0 4px 12px rgba(99, 102, 241, 0.12)' : 'none',
        transition: 'transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, color: '#6B7280', fontWeight: 600 }}>{app.codename}</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginTop: 2 }}>
            {app.label || app.codename}
          </div>
        </div>
        <div style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#DC2626' }}>
            {total.toLocaleString()}
          </div>
          <div style={{ fontSize: 11, color: '#9CA3AF' }}>
            {lang === 'es' ? 'hallazgos' : 'findings'}
          </div>
        </div>
      </div>

      {(app.decision || effortDays > 0) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
          <DecisionBadge decision={app.decision} lang={lang} />
          {effortDays > 0 && (
            <span style={{ fontSize: 11, color: '#6B7280', fontWeight: 600 }}>
              ~{effortDays}d {lang === 'es' ? 'esfuerzo' : 'effort'}
            </span>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#6B7280', marginTop: 10 }}>
        <span>{app.total_files?.toLocaleString() || 0} files</span>
        <span>•</span>
        <span>{app.total_lines?.toLocaleString() || 0} LOC</span>
        <span>•</span>
        <span>risk {app.risk_score?.toLocaleString() || 0}</span>
      </div>

      {app.db_inactive_since && (
        <div style={{
          marginTop: 8, padding: '6px 10px', borderRadius: 8,
          background: '#FEF2F2', border: '1px solid #FECACA',
          fontSize: 11, color: '#991B1B', fontWeight: 600,
        }}>
          {lang === 'es'
            ? `⚠ BD inactiva desde ${app.db_inactive_since}`
            : `⚠ DB inactive since ${app.db_inactive_since}`}
        </div>
      )}

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

const CERT_STATUS_COLORS = {
  complete: { bg: '#DCFCE7', fg: '#166534', border: '#86EFAC', label: 'Complete' },
  in_progress: { bg: '#DBEAFE', fg: '#1E40AF', border: '#93C5FD', label: 'In progress' },
  at_risk: { bg: '#FEF3C7', fg: '#92400E', border: '#FCD34D', label: 'At risk' },
  blocked: { bg: '#FEE2E2', fg: '#991B1B', border: '#FCA5A5', label: 'Blocked' },
}

// Visual styles for pre-assigned refactor decisions on each app card.
// Values match the action strings emitted by the strangler planner
// (refactor / retire / retain / tbd). Unknown actions fall back to a
// neutral gray chip.
const DECISION_STYLES = {
  refactor: { bg: '#EEF2FF', fg: '#3730A3', border: '#C7D2FE', label: 'Refactor' },
  retire:   { bg: '#FEE2E2', fg: '#991B1B', border: '#FCA5A5', label: 'Retire' },
  retain:   { bg: '#DCFCE7', fg: '#166534', border: '#86EFAC', label: 'Retain' },
  tbd:      { bg: '#FEF3C7', fg: '#92400E', border: '#FCD34D', label: 'TBD' },
}

function DecisionBadge({ decision, lang }) {
  if (!decision || !decision.action) return null
  const style = DECISION_STYLES[decision.action] || {
    bg: '#F3F4F6', fg: '#374151', border: '#D1D5DB',
    label: decision.action,
  }
  const phase = decision.phase ? ` · ${decision.phase}` : ''
  return (
    <span style={{
      display: 'inline-block',
      padding: '3px 9px', borderRadius: 10, fontSize: 10, fontWeight: 700,
      background: style.bg, color: style.fg, border: `1px solid ${style.border}`,
      textTransform: 'uppercase', letterSpacing: 0.4, whiteSpace: 'nowrap',
    }}>
      {style.label}{phase}
    </span>
  )
}

function daysBetween(from, to) {
  const msPerDay = 24 * 60 * 60 * 1000
  const diff = to.getTime() - from.getTime()
  return Math.round(diff / msPerDay)
}

function formatDateIso(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return iso
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return iso
  }
}

function CertCard({ cert, lang }) {
  const status = CERT_STATUS_COLORS[cert.status] || CERT_STATUS_COLORS.in_progress
  const due = cert.due_date ? new Date(cert.due_date) : null
  const daysLeft = due ? daysBetween(new Date(), due) : null
  return (
    <div style={{
      background: '#fff', borderRadius: 10, border: '1px solid #E5E7EB',
      padding: '14px 16px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#111827' }}>{cert.name}</div>
          <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{cert.framework}</div>
        </div>
        <div style={{
          padding: '3px 9px', borderRadius: 10, fontSize: 10, fontWeight: 700,
          background: status.bg, color: status.fg, border: `1px solid ${status.border}`,
          textTransform: 'uppercase', letterSpacing: 0.4, whiteSpace: 'nowrap',
        }}>
          {status.label}
        </div>
      </div>
      {cert.description && (
        <div style={{ fontSize: 12, color: '#4B5563', marginTop: 8, lineHeight: 1.5 }}>
          {cert.description.trim()}
        </div>
      )}
      {due && daysLeft !== null && (
        <div style={{ fontSize: 11, color: '#6B7280', marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
          <span>{lang === 'es' ? 'Vence' : 'Due'}: {formatDateIso(cert.due_date)}</span>
          <span style={{ fontWeight: 700, color: daysLeft < 60 ? '#DC2626' : '#374151' }}>
            {daysLeft >= 0
              ? (lang === 'es' ? `${daysLeft}d restantes` : `${daysLeft}d remaining`)
              : (lang === 'es' ? `${-daysLeft}d vencido` : `${-daysLeft}d overdue`)}
          </span>
        </div>
      )}
    </div>
  )
}

function PhaseTimeline({ phases, lang }) {
  if (!phases || phases.length === 0) return null
  const today = new Date()
  return (
    <div style={{ marginTop: 14 }}>
      <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
        {lang === 'es' ? 'Fases del programa' : 'Program phases'}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {phases.map((phase, idx) => {
          const start = phase.start_date ? new Date(phase.start_date) : null
          const end = phase.end_date ? new Date(phase.end_date) : null
          let state = 'future'
          if (start && end) {
            if (today > end) state = 'past'
            else if (today >= start) state = 'current'
          }
          const colors = {
            past: { bg: '#F3F4F6', fg: '#6B7280', accent: '#9CA3AF' },
            current: { bg: '#EEF2FF', fg: '#3730A3', accent: '#6366F1' },
            future: { bg: '#FFFFFF', fg: '#374151', accent: '#D1D5DB' },
          }[state]
          return (
            <div key={idx} style={{
              background: colors.bg, borderRadius: 8,
              border: `1px solid ${colors.accent}`,
              padding: '10px 12px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                <div style={{ fontWeight: 700, fontSize: 13, color: colors.fg }}>
                  {phase.name}
                </div>
                <div style={{ fontSize: 11, color: colors.fg, opacity: 0.8 }}>
                  {formatDateIso(phase.start_date)} → {formatDateIso(phase.end_date)}
                </div>
              </div>
              {phase.milestones?.length > 0 && (
                <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 11, color: colors.fg, opacity: 0.85 }}>
                  {phase.milestones.map((ms, i) => (
                    <li key={i} style={{ marginBottom: 2 }}>{ms}</li>
                  ))}
                </ul>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ComplianceCard({ data, lang, isMobile }) {
  if (!data) return null
  const hardDeadline = data.hard_deadline ? new Date(data.hard_deadline) : null
  const daysLeft = hardDeadline ? daysBetween(new Date(), hardDeadline) : null
  const atRiskCount = (data.certifications || []).filter(c => c.status === 'at_risk' || c.status === 'blocked').length
  const countdownColor = daysLeft !== null
    ? (daysLeft < 30 ? '#DC2626' : daysLeft < 90 ? '#F59E0B' : '#10B981')
    : '#6B7280'
  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: '20px 24px', marginBottom: 24,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ fontSize: 13, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.3 }}>
            {lang === 'es' ? 'Cumplimiento y fecha objetivo' : 'Compliance and hard deadline'}
          </div>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#111827', marginTop: 4 }}>
            {formatDateIso(data.hard_deadline)}
          </div>
          {data.audit_cadence && (
            <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{data.audit_cadence}</div>
          )}
        </div>
        {daysLeft !== null && (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 36, fontWeight: 900, color: countdownColor, lineHeight: 1 }}>
              {daysLeft >= 0 ? daysLeft : `-${-daysLeft}`}
            </div>
            <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>
              {daysLeft >= 0
                ? (lang === 'es' ? 'días restantes' : 'days remaining')
                : (lang === 'es' ? 'días vencido' : 'days overdue')}
            </div>
          </div>
        )}
      </div>

      {data.narrative && (
        <div style={{ fontSize: 13, color: '#4B5563', marginTop: 12, lineHeight: 1.5 }}>
          {data.narrative.trim()}
        </div>
      )}

      {atRiskCount > 0 && (
        <div style={{
          marginTop: 12, padding: '10px 14px', background: '#FEF3C7',
          borderRadius: 8, border: '1px solid #FCD34D',
          fontSize: 12, color: '#92400E', fontWeight: 600,
        }}>
          {lang === 'es'
            ? `⚠️ ${atRiskCount} certificación${atRiskCount > 1 ? 'es' : ''} en riesgo`
            : `⚠️ ${atRiskCount} certification${atRiskCount > 1 ? 's' : ''} at risk`}
        </div>
      )}

      {data.certifications?.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 10, marginTop: 14,
        }}>
          {data.certifications.map((cert, idx) => (
            <CertCard key={idx} cert={cert} lang={lang} />
          ))}
        </div>
      )}

      <PhaseTimeline phases={data.phases} lang={lang} />
    </div>
  )
}

// ── Commercial risk card (Batch 3 follow-up) ───────────────────────────

const LOCK_IN_COLORS = {
  low:    { bg: '#DCFCE7', fg: '#166534', border: '#86EFAC', label: 'Low' },
  medium: { bg: '#FEF3C7', fg: '#92400E', border: '#FCD34D', label: 'Medium' },
  high:   { bg: '#FEE2E2', fg: '#991B1B', border: '#FCA5A5', label: 'High' },
}

function formatUsd(value) {
  const n = Number(value) || 0
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n.toLocaleString()}`
}

// ── EcosystemHealthCard (P-021 + P-009/P-010/P-011 + P-020) ─────────────
//
// One-glance posture panel: ecosystem scale, risk exposure, security
// posture (WAF / Vault alias / NDA status). Consumed from
// GET /refactor/showcase/:tenant_id/ecosystem.
function EcosystemHealthCard({ data, lang, isMobile }) {
  if (!data) return null

  const eco = data.ecosystem || {}
  const risk = data.risk_exposure_usd || {}
  const legal = data.legal || {}
  const edge = data.edge_security || null
  const secret = data.secret_management || null

  const ndaBlocks = legal.nda_status && legal.nda_status !== 'current'
  const ndaColor = ndaBlocks ? '#DC2626' : '#16A34A'
  const ndaLabel = {
    'current':           lang === 'es' ? 'Vigente'            : 'Current',
    'possibly-expired':  lang === 'es' ? 'Posible vencimiento' : 'Possibly expired',
    'expired':           lang === 'es' ? 'Vencido'             : 'Expired',
    'missing':           lang === 'es' ? 'Sin NDA'             : 'Missing',
  }[legal.nda_status] || legal.nda_status

  const riskTotal = Number(risk.total || 0)

  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: '20px 24px', marginBottom: 24,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ fontSize: 13, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.3 }}>
            {lang === 'es' ? 'Salud del ecosistema' : 'Ecosystem health'}
          </div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#111827', marginTop: 4 }}>
            {Number(eco.total_loc || 0).toLocaleString()} LOC · {Number(eco.total_issues || 0).toLocaleString()} {lang === 'es' ? 'hallazgos' : 'issues'}
          </div>
          <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 2 }}>
            {eco.total_apps} {lang === 'es' ? 'aplicaciones' : 'apps'} · {eco.total_components} {lang === 'es' ? 'componentes' : 'components'}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 28, fontWeight: 900, color: '#DC2626', lineHeight: 1 }}>
            {formatUsd(riskTotal)}
          </div>
          <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>
            {lang === 'es' ? 'exposición total' : 'total exposure'}
          </div>
        </div>
      </div>

      {/* KPI row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
        gap: 12, marginTop: 16,
      }}>
        <KpiCard
          label={lang === 'es' ? 'Críticos' : 'Critical issues'}
          value={Number(eco.critical_issues || 0).toLocaleString()}
          subtitle={`${Number(eco.critical_density_pct || 0).toFixed(1)}% density`}
          color="#DC2626"
        />
        <KpiCard
          label="SQL concat"
          value={`+${Number(eco.sql_concat_queries || 0).toLocaleString()}`}
          subtitle={`${Number(eco.tables_without_fk_pct || 0).toFixed(0)}% ${lang === 'es' ? 'tablas sin FK' : 'tables no FK'}`}
          color="#EA580C"
        />
        <KpiCard
          label={lang === 'es' ? 'Apps sin tests' : 'Apps no tests'}
          value={`${eco.apps_without_tests || 0}/12`}
          subtitle={`${eco.apps_without_cicd || 0}/12 ${lang === 'es' ? 'sin CI/CD' : 'no CI/CD'}`}
          color="#7C3AED"
        />
        <KpiCard
          label={lang === 'es' ? 'PII' : 'PII items'}
          value={eco.pii_items || 0}
          subtitle={`${eco.pii_inputs || 0} ${lang === 'es' ? 'entradas' : 'inputs'}`}
          color="#0E7490"
        />
      </div>

      {/* Security posture row */}
      <div style={{
        marginTop: 20, padding: '14px 16px', background: '#F9FAFB', borderRadius: 8,
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)',
        gap: 12,
      }}>
        {/* Edge security (WAF) */}
        <div>
          <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.3 }}>
            {lang === 'es' ? 'Edge security' : 'Edge security'}
          </div>
          <div style={{ fontSize: 14, fontWeight: 700, color: edge?.waf_present ? '#16A34A' : '#9CA3AF', marginTop: 4 }}>
            {edge?.waf_present ? `WAF ${edge.waf_provider || ''}` : (lang === 'es' ? 'Sin WAF' : 'No WAF')}
          </div>
          {edge?.geo_blocking?.length > 0 && (
            <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>
              {lang === 'es' ? 'Bloquea' : 'Blocks'}: {edge.geo_blocking.join(', ')}
            </div>
          )}
          {edge?.pattern_rules?.length > 0 && (
            <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>
              {lang === 'es' ? 'Reglas' : 'Rules'}: {edge.pattern_rules.join(', ')}
            </div>
          )}
        </div>

        {/* Secret management (Bolt/Vault) */}
        <div>
          <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.3 }}>
            {lang === 'es' ? 'Gestión de secretos' : 'Secret management'}
          </div>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#111827', marginTop: 4 }}>
            {secret?.product || (lang === 'es' ? 'No configurado' : 'Not configured')}
            {secret?.internal_alias && <span style={{ color: '#6B7280', fontWeight: 500 }}> · {secret.internal_alias}</span>}
          </div>
          {secret && (
            <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>
              {secret.on_premise ? (lang === 'es' ? 'On-premise' : 'On-premise') : (lang === 'es' ? 'Nube' : 'Cloud')}
              {' · '}
              {secret.rotation_policy}
              {secret.hash_based_injection && (lang === 'es' ? ' · hash-inject' : ' · hash-inject')}
            </div>
          )}
        </div>

        {/* Legal / NDA */}
        <div>
          <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.3 }}>
            {lang === 'es' ? 'Estado legal (NDA)' : 'Legal status (NDA)'}
          </div>
          <div style={{ fontSize: 14, fontWeight: 700, color: ndaColor, marginTop: 4 }}>
            {ndaLabel || (lang === 'es' ? 'Desconocido' : 'Unknown')}
          </div>
          {legal.nda_signed_date && (
            <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>
              {lang === 'es' ? 'Firmado' : 'Signed'}: {legal.nda_signed_date}
            </div>
          )}
          {legal.renewal_required_before_transfer && (
            <div style={{ fontSize: 11, color: '#DC2626', fontWeight: 600, marginTop: 2 }}>
              ⚠ {lang === 'es' ? 'Renovación requerida' : 'Renewal required'}
            </div>
          )}
        </div>
      </div>

      {/* Per-app critical density ranking (top 3) */}
      {data.per_app?.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.3 }}>
            {lang === 'es' ? 'Top densidad crítica por app' : 'Top critical density per app'}
          </div>
          <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {[...data.per_app]
              .filter(a => a.total_issues > 0)
              .sort((a, b) => b.critical_density_pct - a.critical_density_pct)
              .slice(0, 3)
              .map(a => (
                <div key={a.app} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <div style={{ color: '#374151' }}>
                    <code style={{ fontSize: 11, color: '#6B7280' }}>{a.app}</code>
                    {' '}
                    <span>{a.label}</span>
                  </div>
                  <div style={{ color: a.critical_density_pct >= 50 ? '#DC2626' : '#374151', fontWeight: 600 }}>
                    {a.critical_density_pct.toFixed(1)}% · {a.critical_issues}/{a.total_issues}
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}

function CommercialRiskCard({ data, lang, isMobile }) {
  if (!data) return null
  const vendors = data.vendors || []
  const penalties = data.penalty_exposure || []
  const gap = Number(data.contract_gap_pct || 0)
  const exposure = Number(data.total_exposure_usd || 0)
  const gapColor = gap >= 30 ? '#DC2626' : gap >= 15 ? '#F59E0B' : '#10B981'

  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: '20px 24px', marginBottom: 24,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ fontSize: 13, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.3 }}>
            {lang === 'es' ? 'Riesgo comercial' : 'Commercial risk'}
          </div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#111827', marginTop: 4 }}>
            {formatUsd(exposure)} {lang === 'es' ? 'exposición total' : 'total exposure'}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 28, fontWeight: 900, color: gapColor, lineHeight: 1 }}>
            {gap.toFixed(0)}%
          </div>
          <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>
            {lang === 'es' ? 'gap de contrato' : 'contract gap'}
          </div>
        </div>
      </div>

      {data.narrative && (
        <div style={{ fontSize: 13, color: '#4B5563', marginTop: 12, lineHeight: 1.5 }}>
          {data.narrative.trim()}
        </div>
      )}

      {vendors.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
            {lang === 'es' ? 'Dependencias de vendors' : 'Vendor dependencies'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {vendors.map((v, idx) => {
              const lock = LOCK_IN_COLORS[v.lock_in_level] || LOCK_IN_COLORS.medium
              return (
                <div key={idx} style={{
                  padding: '10px 12px', background: '#F9FAFB', borderRadius: 8,
                }}>
                  {isMobile ? (
                    // Mobile: stack name on top, then a row of metrics below
                    <>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 13, fontWeight: 700, color: '#111827', fontFamily: 'monospace', wordBreak: 'break-word' }}>
                            {v.name}
                          </div>
                          <div style={{ fontSize: 11, color: '#6B7280' }}>{v.category}</div>
                        </div>
                        <div style={{
                          padding: '3px 8px', borderRadius: 10, fontSize: 9, fontWeight: 700,
                          background: lock.bg, color: lock.fg, border: `1px solid ${lock.border}`,
                          textTransform: 'uppercase', whiteSpace: 'nowrap',
                        }}>
                          {lock.label}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#6B7280' }}>
                        <span>{Number(v.revenue_share_pct || 0).toFixed(1)}% rev</span>
                        <span>•</span>
                        <span>{formatUsd(v.spend_2y_usd)} / 2y</span>
                      </div>
                    </>
                  ) : (
                    // Desktop: original 4-column grid
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: '1.2fr auto auto auto',
                      gap: 10, alignItems: 'center',
                    }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#111827', fontFamily: 'monospace' }}>
                          {v.name}
                        </div>
                        <div style={{ fontSize: 11, color: '#6B7280' }}>{v.category}</div>
                      </div>
                      <div style={{
                        padding: '3px 9px', borderRadius: 10, fontSize: 10, fontWeight: 700,
                        background: lock.bg, color: lock.fg, border: `1px solid ${lock.border}`,
                        textTransform: 'uppercase', whiteSpace: 'nowrap',
                      }}>
                        lock-in: {lock.label}
                      </div>
                      <div style={{ fontSize: 11, color: '#6B7280', whiteSpace: 'nowrap' }}>
                        {Number(v.revenue_share_pct || 0).toFixed(1)}% rev
                      </div>
                      <div style={{ fontSize: 11, color: '#6B7280', whiteSpace: 'nowrap' }}>
                        {formatUsd(v.spend_2y_usd)} / 2y
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {penalties.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
            {lang === 'es' ? 'Exposición por penalidad' : 'Penalty exposure'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {penalties.map((p, idx) => {
              const pct = exposure > 0 ? (Number(p.cap_usd || 0) / exposure) * 100 : 0
              return (
                <div key={idx}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                    <span style={{ color: '#374151', fontWeight: 600, textTransform: 'capitalize' }}>
                      {p.category}
                    </span>
                    <span style={{ color: '#DC2626', fontWeight: 700 }}>
                      {formatUsd(p.cap_usd)}
                    </span>
                  </div>
                  <div style={{ height: 6, background: '#F3F4F6', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{
                      width: `${pct}%`, height: '100%',
                      background: 'linear-gradient(90deg, #F87171, #DC2626)',
                      transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                    }} />
                  </div>
                  {p.driver && (
                    <div style={{ fontSize: 10, color: '#9CA3AF', marginTop: 2, fontStyle: 'italic' }}>
                      {p.driver}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Governance card (Batch 3 follow-up) ────────────────────────────────

const TECH_LEAD_STATUS = {
  unfilled:   { bg: '#FEE2E2', fg: '#991B1B', border: '#FCA5A5', label: 'Unfilled' },
  recruiting: { bg: '#FEF3C7', fg: '#92400E', border: '#FCD34D', label: 'Recruiting' },
  hired:      { bg: '#DBEAFE', fg: '#1E40AF', border: '#93C5FD', label: 'Hired' },
  onboarding: { bg: '#E0E7FF', fg: '#3730A3', border: '#A5B4FC', label: 'Onboarding' },
}

function GovernanceCard({ data, lang, isMobile }) {
  if (!data) return null
  const teams = data.teams || []
  const steering = data.steering
  const codeAccess = data.code_access
  const techLead = data.tech_lead
  const techLeadStyle = techLead
    ? TECH_LEAD_STATUS[techLead.status] || TECH_LEAD_STATUS.unfilled
    : null

  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: '20px 24px', marginBottom: 24,
    }}>
      <div style={{ fontSize: 13, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.3 }}>
        {lang === 'es' ? 'Gobernanza del programa' : 'Program governance'}
      </div>

      {data.narrative && (
        <div style={{ fontSize: 13, color: '#4B5563', marginTop: 10, lineHeight: 1.5 }}>
          {data.narrative.trim()}
        </div>
      )}

      {steering && (
        <div style={{
          marginTop: 14, padding: '12px 14px', background: '#F9FAFB',
          borderRadius: 8, borderLeft: '3px solid #6366F1',
        }}>
          <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>
            {lang === 'es' ? 'Comité de dirección' : 'Steering committee'}
          </div>
          <div style={{ fontSize: 13, color: '#111827', fontWeight: 600 }}>{steering.cadence}</div>
          {steering.owner_role && (
            <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>
              {lang === 'es' ? 'Presidente' : 'Chair'}: {steering.owner_role}
            </div>
          )}
          {steering.first_formal_review && (
            <div style={{ fontSize: 11, color: '#6B7280' }}>
              {lang === 'es' ? 'Primera revisión formal' : 'First formal review'}: {formatDateIso(steering.first_formal_review)}
            </div>
          )}
          {steering.attendees && steering.attendees.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
              {steering.attendees.map((a, i) => (
                <span key={i} style={{
                  fontSize: 10, padding: '2px 6px', borderRadius: 6,
                  background: '#EEF2FF', color: '#3730A3', fontWeight: 600,
                }}>{a}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {teams.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
            {lang === 'es' ? 'Equipos de entrega' : 'Delivery teams'}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
            {teams.map((t, idx) => (
              <div key={idx} style={{
                padding: '10px 12px', background: '#F9FAFB', borderRadius: 8,
                border: '1px solid #E5E7EB',
              }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#111827', fontFamily: 'monospace' }}>
                  {t.name}
                </div>
                <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>
                  {t.role} · {t.headcount} {lang === 'es' ? 'personas' : 'people'}
                </div>
                {t.app_scope && t.app_scope.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                    {t.app_scope.map((a, i) => (
                      <span key={i} style={{
                        fontSize: 9, padding: '2px 5px', borderRadius: 4,
                        background: '#E0E7FF', color: '#3730A3', fontFamily: 'monospace',
                      }}>{a}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {codeAccess && (
        <div style={{
          marginTop: 14, padding: '12px 14px',
          background: codeAccess.bottleneck ? '#FEF2F2' : '#F9FAFB',
          borderRadius: 8,
          borderLeft: `3px solid ${codeAccess.bottleneck ? '#DC2626' : '#9CA3AF'}`,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>
              {lang === 'es' ? 'Acceso al código' : 'Code access gate'}
            </div>
            {codeAccess.bottleneck && (
              <span style={{
                fontSize: 9, padding: '2px 7px', borderRadius: 10,
                background: '#FEE2E2', color: '#991B1B', fontWeight: 700,
                textTransform: 'uppercase',
              }}>
                {lang === 'es' ? 'Cuello de botella' : 'Bottleneck'}
              </span>
            )}
          </div>
          <div style={{ fontSize: 13, color: '#111827', fontWeight: 600, fontFamily: 'monospace', marginTop: 4 }}>
            {codeAccess.model}
          </div>
          {codeAccess.owner_role && (
            <div style={{ fontSize: 11, color: '#6B7280' }}>
              {lang === 'es' ? 'Dueño' : 'Owner'}: {codeAccess.owner_role}
            </div>
          )}
          {codeAccess.notes && (
            <div style={{ fontSize: 11, color: '#4B5563', marginTop: 6, fontStyle: 'italic' }}>
              {codeAccess.notes.trim()}
            </div>
          )}
        </div>
      )}

      {techLead && (
        <div style={{
          marginTop: 14, padding: '12px 14px', background: '#F9FAFB',
          borderRadius: 8, borderLeft: '3px solid #8B5CF6',
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10, flexWrap: 'wrap',
        }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>
              {lang === 'es' ? 'Tech lead post-lanzamiento' : 'Post-launch tech lead'}
            </div>
            {techLead.scope && (
              <div style={{ fontSize: 12, color: '#4B5563', lineHeight: 1.4 }}>
                {techLead.scope.trim()}
              </div>
            )}
            {techLead.target_start_date && (
              <div style={{ fontSize: 11, color: '#6B7280', marginTop: 4 }}>
                {lang === 'es' ? 'Inicio objetivo' : 'Target start'}: {formatDateIso(techLead.target_start_date)}
              </div>
            )}
          </div>
          {techLeadStyle && (
            <span style={{
              padding: '4px 10px', borderRadius: 10, fontSize: 10, fontWeight: 700,
              background: techLeadStyle.bg, color: techLeadStyle.fg,
              border: `1px solid ${techLeadStyle.border}`,
              textTransform: 'uppercase', letterSpacing: 0.4, whiteSpace: 'nowrap',
            }}>
              {techLeadStyle.label}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

// ── Report Out modal (Batch 3 follow-up) ───────────────────────────────

/**
 * Tiny markdown-to-HTML converter for the Report Out modal. Intentionally
 * minimal — handles headers (# through ###), bold (**text**), bullet
 * lists, tables with pipes, and paragraphs. Safer than pulling in a
 * full markdown library for one view.
 */
// Minimal HTML-entity escape for user-supplied markdown text.
// Report Out markdown is backend-generated + confidence-trusted, but we
// escape defensively before injecting into the DOM via dangerouslySetInnerHTML.
// Runs BEFORE the inline markdown substitutions so the emitted tags remain
// real HTML while any stray `<script>` / `<img onerror=…>` in the source
// text turns into inert entities.
function escapeHtml(s) {
  if (s == null) return ''
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderMarkdown(md) {
  if (!md) return ''
  const lines = md.split('\n')
  const html = []
  let inList = false
  let inTable = false
  let tableRows = []

  const flushTable = () => {
    if (!tableRows.length) return
    const header = tableRows[0]
    const body = tableRows.slice(2)  // skip separator row
    html.push('<table style="width:100%;border-collapse:collapse;margin:12px 0;font-size:12px">')
    html.push('<thead><tr>')
    for (const cell of header) {
      html.push(`<th style="padding:6px 10px;border:1px solid #E5E7EB;background:#F9FAFB;text-align:left">${cell}</th>`)
    }
    html.push('</tr></thead><tbody>')
    for (const row of body) {
      html.push('<tr>')
      for (const cell of row) {
        html.push(`<td style="padding:6px 10px;border:1px solid #E5E7EB">${cell}</td>`)
      }
      html.push('</tr>')
    }
    html.push('</tbody></table>')
    tableRows = []
    inTable = false
  }

  const flushList = () => {
    if (inList) {
      html.push('</ul>')
      inList = false
    }
  }

  // Escape first, then apply markdown inline tokens. The whitelist of
  // tokens we emit (<code>, <strong>, <em>) is intentionally small —
  // everything else stays entity-encoded.
  const inline = (text) => {
    return escapeHtml(text)
      .replace(/`([^`]+)`/g, '<code style="background:#F3F4F6;padding:1px 5px;border-radius:4px;font-family:monospace;font-size:0.9em">$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/_([^_]+)_/g, '<em>$1</em>')
  }

  for (const raw of lines) {
    const line = raw.trimEnd()

    // Table detection
    if (line.startsWith('|') && line.endsWith('|')) {
      flushList()
      const cells = line.slice(1, -1).split('|').map(c => inline(c.trim()))
      tableRows.push(cells)
      inTable = true
      continue
    }
    if (inTable) flushTable()

    // Headings
    if (line.startsWith('### ')) {
      flushList()
      html.push(`<h3 style="margin:16px 0 8px;font-size:14px;color:#111827">${inline(line.slice(4))}</h3>`)
      continue
    }
    if (line.startsWith('## ')) {
      flushList()
      html.push(`<h2 style="margin:20px 0 10px;font-size:16px;color:#111827;border-bottom:1px solid #E5E7EB;padding-bottom:4px">${inline(line.slice(3))}</h2>`)
      continue
    }
    if (line.startsWith('# ')) {
      flushList()
      html.push(`<h1 style="margin:0 0 12px;font-size:20px;color:#111827">${inline(line.slice(2))}</h1>`)
      continue
    }

    // Horizontal rule
    if (line === '---') {
      flushList()
      html.push('<hr style="border:none;border-top:1px solid #E5E7EB;margin:16px 0" />')
      continue
    }

    // Bullet list
    if (/^\s*[-*]\s+/.test(line)) {
      if (!inList) {
        html.push('<ul style="margin:8px 0;padding-left:20px;font-size:13px;color:#374151">')
        inList = true
      }
      html.push(`<li style="margin:2px 0">${inline(line.replace(/^\s*[-*]\s+/, ''))}</li>`)
      continue
    }
    flushList()

    // Blank line
    if (line === '') {
      continue
    }

    // Default paragraph
    html.push(`<p style="margin:8px 0;font-size:13px;color:#374151;line-height:1.5">${inline(line)}</p>`)
  }
  flushTable()
  flushList()
  return html.join('')
}

function ReportOutModal({ markdown, onClose, lang }) {
  const isMobile = useIsMobile()
  if (!markdown) return null
  const handleDownload = () => {
    try {
      const blob = new Blob([markdown], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'report_out.md'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('download failed', e)
    }
  }
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.75)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 1000, padding: isMobile ? 8 : 20,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 12, maxWidth: 900, width: '100%',
          maxHeight: isMobile ? '95vh' : '90vh',
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
        }}
      >
        <div style={{
          padding: isMobile ? '12px 14px' : '16px 20px',
          borderBottom: '1px solid #E5E7EB',
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', gap: 8, flexWrap: 'wrap',
        }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#111827' }}>
            {lang === 'es' ? 'Reporte ejecutivo' : 'Executive Report Out'}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={handleDownload}
              style={{
                padding: '6px 12px', borderRadius: 6, border: '1px solid #D1D5DB',
                background: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                color: '#374151',
              }}
            >
              {lang === 'es' ? 'Descargar .md' : 'Download .md'}
            </button>
            <button
              onClick={onClose}
              style={{
                padding: '6px 12px', borderRadius: 6, border: 'none',
                background: '#111827', color: '#fff', fontSize: 12, fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {lang === 'es' ? 'Cerrar' : 'Close'}
            </button>
          </div>
        </div>
        <div
          style={{
            padding: isMobile ? '14px 16px' : '20px 28px',
            overflow: 'auto',
            overflowWrap: 'break-word',
            flex: 1,
            color: '#374151',
            fontSize: isMobile ? 12 : 13,
          }}
          dangerouslySetInnerHTML={{ __html: renderMarkdown(markdown) }}
        />
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
  const [compliance, setCompliance] = useState(null)
  const [commercialRisk, setCommercialRisk] = useState(null)
  const [governance, setGovernance] = useState(null)
  const [ecosystem, setEcosystem] = useState(null)
  const [reportOutMd, setReportOutMd] = useState(null)
  const [reportOutLoading, setReportOutLoading] = useState(false)
  const [reportOutOpen, setReportOutOpen] = useState(false)

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

  // Load the ecosystem posture (P-021 + P-009/P-010/P-011 + P-020).
  // Independent of the main report and silent on 404 (same pattern as compliance).
  useEffect(() => {
    let cancelled = false
    fetchAPI(`/refactor/showcase/${tenantId}/ecosystem`).then(res => {
      if (cancelled) return
      if (!res.error && res.data) {
        setEcosystem(res.data)
      }
    })
    return () => { cancelled = true }
  }, [])

  // Load the compliance profile (independent of the main report)
  useEffect(() => {
    let cancelled = false
    fetchAPI(`/refactor/showcase/${tenantId}/compliance`).then(res => {
      if (cancelled) return
      if (!res.error && res.data) {
        setCompliance(res.data)
      }
      // Compliance absence is silent — endpoint returns 404 if the tenant
      // has no compliance profile, and the rest of the page should still render.
    })
    return () => { cancelled = true }
  }, [])

  // Load the commercial risk profile
  useEffect(() => {
    let cancelled = false
    fetchAPI(`/refactor/showcase/${tenantId}/commercial-risk`).then(res => {
      if (cancelled) return
      if (!res.error && res.data) setCommercialRisk(res.data)
    })
    return () => { cancelled = true }
  }, [])

  // Load the governance profile
  useEffect(() => {
    let cancelled = false
    fetchAPI(`/refactor/showcase/${tenantId}/governance`).then(res => {
      if (cancelled) return
      if (!res.error && res.data) setGovernance(res.data)
    })
    return () => { cancelled = true }
  }, [])

  // Lazy-load the Report Out markdown only when the user opens the modal
  const openReportOut = async () => {
    setReportOutOpen(true)
    if (reportOutMd) return  // already loaded
    setReportOutLoading(true)
    const res = await fetchAPI(`/refactor/showcase/${tenantId}/report-out`)
    if (!res.error && res.data?.markdown) {
      setReportOutMd(res.data.markdown)
    }
    setReportOutLoading(false)
  }

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
    // Skeleton screen — mirrors the real layout so the transition to
    // loaded state does not shift elements around. Uses a gentle CSS
    // shimmer animation defined inline.
    const shimmer = {
      background: 'linear-gradient(90deg, #F3F4F6 0%, #E5E7EB 50%, #F3F4F6 100%)',
      backgroundSize: '200% 100%',
      animation: 'nf-shimmer 1.4s ease-in-out infinite',
      borderRadius: 8,
    }
    return (
      <div style={{ padding: isMobile ? 16 : 32, maxWidth: 1400, margin: '0 auto' }}>
        <style>{`
          @keyframes nf-shimmer {
            0%   { background-position: 200% 0; }
            100% { background-position: -200% 0; }
          }
        `}</style>
        <div style={{ ...shimmer, width: '60%', height: 28, marginBottom: 8 }} />
        <div style={{ ...shimmer, width: '80%', height: 14, marginBottom: 24 }} />
        <div style={{ ...shimmer, width: '100%', height: 140, marginBottom: 24 }} />
        <div style={{ ...shimmer, width: 260, height: 42, marginBottom: 20 }} />
        <div style={{ ...shimmer, width: '100%', height: 180, marginBottom: 16 }} />
        <div style={{ ...shimmer, width: '100%', height: 180, marginBottom: 16 }} />
        <div style={{ ...shimmer, width: '100%', height: 180, marginBottom: 24 }} />
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
          gap: isMobile ? 14 : 20, marginTop: 16,
        }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: isMobile ? 26 : 32, fontWeight: 800, lineHeight: 1.1 }}>
              {totals.apps || 0}
            </div>
            <div style={{ fontSize: 11, opacity: 0.85, marginTop: 2 }}>
              {lang === 'es' ? 'Aplicaciones' : 'Applications'}
            </div>
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: isMobile ? 22 : 32, fontWeight: 800, lineHeight: 1.1, overflowWrap: 'break-word' }}>
              {(totals.lines_of_code || 0).toLocaleString()}
            </div>
            <div style={{ fontSize: 11, opacity: 0.85, marginTop: 2 }}>
              {lang === 'es' ? 'Líneas de código' : 'Lines of code'}
            </div>
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: isMobile ? 22 : 32, fontWeight: 800, lineHeight: 1.1, overflowWrap: 'break-word' }}>
              {(totals.findings || 0).toLocaleString()}
            </div>
            <div style={{ fontSize: 11, opacity: 0.85, marginTop: 2 }}>
              {lang === 'es' ? 'Hallazgos' : 'Findings'}
            </div>
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: isMobile ? 26 : 32, fontWeight: 800, lineHeight: 1.1 }}>
              {durationSec}s
            </div>
            <div style={{ fontSize: 11, opacity: 0.85, marginTop: 2 }}>
              {lang === 'es' ? 'Duración' : 'Duration'}
            </div>
          </div>
        </div>
      </div>

      {/* Action bar — Report Out + future download actions */}
      <div style={{
        display: 'flex', gap: isMobile ? 6 : 12, marginBottom: 20,
        flexDirection: isMobile ? 'column' : 'row',
        alignItems: isMobile ? 'stretch' : 'center',
      }}>
        <button
          onClick={openReportOut}
          disabled={reportOutLoading}
          style={{
            padding: isMobile ? '12px 18px' : '10px 18px',
            borderRadius: 8,
            background: reportOutLoading ? '#A5B4FC' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
            color: '#fff', border: 'none',
            fontSize: isMobile ? 14 : 13,
            fontWeight: 700,
            cursor: reportOutLoading ? 'default' : 'pointer',
            boxShadow: '0 2px 6px rgba(99, 102, 241, 0.3)',
            whiteSpace: 'nowrap',
          }}
        >
          {reportOutLoading
            ? (lang === 'es' ? 'Cargando reporte...' : 'Loading report...')
            : (lang === 'es' ? '📄 Ver reporte ejecutivo' : '📄 View Executive Report Out')}
        </button>
        <span style={{
          fontSize: 11, color: '#6B7280',
          textAlign: isMobile ? 'center' : 'left',
        }}>
          {lang === 'es'
            ? 'Resumen completo del tenant — listo para stakeholders.'
            : 'Single-document summary — ready for stakeholders.'}
        </span>
      </div>

      {/* Ecosystem posture (P-021 + P-009/P-010/P-011 + P-020 — 2026-04-13) */}
      <EcosystemHealthCard data={ecosystem} lang={lang} isMobile={isMobile} />

      {/* Compliance countdown (Batch 3, deliverable D) */}
      <ComplianceCard data={compliance} lang={lang} isMobile={isMobile} />

      {/* Commercial risk (Batch 3 follow-up) */}
      <CommercialRiskCard data={commercialRisk} lang={lang} isMobile={isMobile} />

      {/* Governance (Batch 3 follow-up) */}
      <GovernanceCard data={governance} lang={lang} isMobile={isMobile} />

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
                      transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                    }} />
                  </div>
                </div>
              )
            })}
        </div>
      )}

      {/* App grid + strangler detail.
          Desktop: 2-column split, all apps on the left, plan on the right.
          Mobile:  single column, plan renders inline underneath the
                   selected app card so users don't scroll past 5 cards. */}
      {(() => {
        const planPanel = (
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
        )

        if (isMobile) {
          // Mobile: interleave the plan directly under the selected app card
          return (
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 13, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 10 }}>
                {lang === 'es' ? 'Aplicaciones' : 'Applications'}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {(report.apps || []).map(app => (
                  <div key={app.codename}>
                    <AppCard
                      app={app}
                      onSelect={setSelectedApp}
                      selected={selectedApp === app.codename}
                      lang={lang}
                    />
                    {selectedApp === app.codename && (
                      <div style={{ marginTop: 12, marginLeft: 0 }}>
                        {planPanel}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        }

        // Desktop: classic 2-column split
        return (
          <div style={{
            display: 'grid',
            gridTemplateColumns: '380px 1fr',
            gap: 16, marginBottom: 24,
          }}>
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
                    lang={lang}
                  />
                ))}
              </div>
            </div>
            {planPanel}
          </div>
        )
      })()}

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

      {/* Report Out modal overlay (mounted outside the normal flow) */}
      {reportOutOpen && (
        <ReportOutModal
          markdown={reportOutMd}
          onClose={() => setReportOutOpen(false)}
          lang={lang}
        />
      )}

    </div>
  )
}
