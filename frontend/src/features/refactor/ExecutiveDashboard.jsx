import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'
import { useIsMobile } from '../../shared/hooks/useIsMobile'

/**
 * Executive Dashboard — C-Level view of remediation progress.
 *
 * Designed for enterprise executives (CEO, CTO, CFO, CISO):
 * - Risk reduction over time
 * - Issues fixed vs remaining (by severity)
 * - PII exposure status
 * - Estimated timeline to completion
 * - Cost savings from auto-fixes
 */

const SEVERITY_COLORS = {
  critical: '#DC2626',
  blocker: '#B91C1C',
  high: '#F59E0B',
  medium: '#3B82F6',
  low: '#9CA3AF',
  info: '#D1D5DB',
}

const CATEGORY_ICONS = {
  sql_injection: { icon: '💉', label: 'SQL Injection' },
  hardcoded_cred: { icon: '🔑', label: 'Credentials' },
  pii_exposure: { icon: '🛡️', label: 'PII Exposure' },
  xss: { icon: '⚠️', label: 'XSS' },
  missing_auth: { icon: '🔓', label: 'Missing Auth' },
  weak_crypto: { icon: '🔐', label: 'Weak Crypto' },
  info_leak: { icon: '📢', label: 'Info Leak' },
  missing_test: { icon: '🧪', label: 'No Tests' },
  code_quality: { icon: '📋', label: 'Code Quality' },
}

function KPI({ label, value, subtitle, color, trend }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 14, border: '1px solid #E5E7EB',
      padding: 20, minWidth: 140,
    }}>
      <div style={{ fontSize: 12, color: '#9CA3AF', fontWeight: 500, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color: color || '#111827', lineHeight: 1.1 }}>{value}</div>
      {subtitle && <div style={{ fontSize: 12, color: '#6B7280', marginTop: 4 }}>{subtitle}</div>}
      {trend && (
        <div style={{ fontSize: 11, marginTop: 4, color: trend > 0 ? '#10B981' : '#EF4444', fontWeight: 600 }}>
          {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% vs last week
        </div>
      )}
    </div>
  )
}

function RiskMeter({ score, maxScore, label }) {
  const pct = Math.min(100, (score / Math.max(maxScore, 1)) * 100)
  const color = pct > 70 ? '#DC2626' : pct > 40 ? '#F59E0B' : '#10B981'
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color }}>{pct.toFixed(0)}%</span>
      </div>
      <div style={{ height: 8, background: '#F3F4F6', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`, background: color,
          borderRadius: 4, transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  )
}

function SeverityBar({ data }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1
  return (
    <div style={{ display: 'flex', height: 28, borderRadius: 6, overflow: 'hidden', marginBottom: 8 }}>
      {Object.entries(data).map(([sev, count]) => (
        <div
          key={sev}
          title={`${sev}: ${count.toLocaleString()}`}
          style={{
            width: `${(count / total) * 100}%`,
            background: SEVERITY_COLORS[sev] || '#9CA3AF',
            minWidth: count > 0 ? 2 : 0,
            transition: 'width 0.3s',
          }}
        />
      ))}
    </div>
  )
}

function BatchTimeline({ batches, lang }) {
  return (
    <div>
      {batches.map((b, i) => (
        <div key={i} style={{
          display: 'flex', gap: 12, marginBottom: 12, alignItems: 'flex-start',
        }}>
          {/* Timeline dot + line */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 24 }}>
            <div style={{
              width: 12, height: 12, borderRadius: '50%',
              background: i === 0 ? '#6366F1' : '#D1D5DB',
              border: i === 0 ? '3px solid #C7D2FE' : 'none',
            }} />
            {i < batches.length - 1 && (
              <div style={{ width: 2, flex: 1, background: '#E5E7EB', minHeight: 30 }} />
            )}
          </div>

          {/* Batch card */}
          <div style={{
            flex: 1, background: i === 0 ? '#EEF2FF' : '#F9FAFB',
            borderRadius: 10, padding: 14, border: `1px solid ${i === 0 ? '#C7D2FE' : '#E5E7EB'}`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#111827' }}>
                {lang === 'es' ? `Lote ${b.batch}` : `Batch ${b.batch}`}: {b.name}
              </span>
              <span style={{
                fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 4,
                background: '#D1FAE5', color: '#059669',
              }}>
                {b.risk_reduction}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#6B7280' }}>
              <span>{b.issues.toLocaleString()} issues</span>
              <span style={{ color: '#10B981', fontWeight: 600 }}>{b.auto_fixable} auto</span>
              <span>{b.manual} manual</span>
              <span>~{b.estimated_hours}h</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function ExecutiveDashboard({ lang = 'es' }) {
  const isMobile = useIsMobile()
  const [repoPath, setRepoPath] = useState('')
  const [loading, setLoading] = useState(false)
  const [triageData, setTriageData] = useState(null)
  const [piiData, setPiiData] = useState(null)
  const [dbData, setDbData] = useState(null)
  const [error, setError] = useState(null)

  const handleAnalyze = async () => {
    if (!repoPath.trim()) return
    setLoading(true)
    setError(null)

    try {
      const [triageRes, piiRes, dbRes] = await Promise.all([
        fetchAPI('/refactor/triage', { method: 'POST', body: JSON.stringify({ project_path: repoPath }) }),
        fetchAPI('/refactor/scan-pii', { method: 'POST', body: JSON.stringify({ project_path: repoPath }) }),
        fetchAPI('/refactor/scan-db', { method: 'POST', body: JSON.stringify({ project_path: repoPath }) }),
      ])

      if (triageRes.data) setTriageData(triageRes.data)
      if (piiRes.data) setPiiData(piiRes.data)
      if (dbRes.data) setDbData(dbRes.data)
      if (triageRes.error && piiRes.error && dbRes.error) setError(triageRes.error)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  const t = triageData?.summary || {}
  const p = piiData?.summary || {}
  const d = dbData?.summary || {}

  return (
    <div style={{ padding: isMobile ? 16 : 32, maxWidth: 1400, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, color: '#111827', marginBottom: 4 }}>
          {lang === 'es' ? 'Panel Ejecutivo de Remediacion' : 'Executive Remediation Dashboard'}
        </h1>
        <p style={{ fontSize: 14, color: '#6B7280' }}>
          {lang === 'es'
            ? 'Vision C-Level del progreso de remediacion, riesgo y cumplimiento.'
            : 'C-Level view of remediation progress, risk, and compliance.'}
        </p>
      </div>

      {/* Input */}
      <div style={{
        background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
        padding: 16, marginBottom: 24, display: 'flex', gap: 8, flexWrap: 'wrap',
      }}>
        <input
          value={repoPath}
          onChange={e => setRepoPath(e.target.value)}
          placeholder={lang === 'es' ? 'Ruta del repositorio...' : 'Repository path...'}
          style={{
            flex: 1, minWidth: 250, padding: '10px 14px', borderRadius: 8,
            border: '1px solid #D1D5DB', fontSize: 14, fontFamily: 'monospace',
          }}
        />
        <button
          onClick={handleAnalyze}
          disabled={loading || !repoPath.trim()}
          style={{
            padding: '10px 24px', borderRadius: 8, border: 'none',
            background: loading ? '#A5B4FC' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
            color: '#fff', fontWeight: 700, fontSize: 14, cursor: loading ? 'default' : 'pointer',
          }}
        >
          {loading
            ? (lang === 'es' ? 'Analizando...' : 'Analyzing...')
            : (lang === 'es' ? 'Analizar Sistema' : 'Analyze System')}
        </button>
      </div>

      {error && (
        <div style={{ padding: 14, background: '#FEE2E2', borderRadius: 8, color: '#DC2626', fontSize: 13, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* KPI Row */}
      {triageData && (
        <>
          <div style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(5, 1fr)',
            gap: 12, marginBottom: 24,
          }}>
            <KPI
              label={lang === 'es' ? 'Total Issues' : 'Total Issues'}
              value={t.total_issues?.toLocaleString() || '0'}
              subtitle={`${t.critical?.toLocaleString() || 0} critical`}
              color="#111827"
            />
            <KPI
              label={lang === 'es' ? 'Auto-Fixable' : 'Auto-Fixable'}
              value={t.auto_fixable?.toLocaleString() || '0'}
              subtitle={`${t.estimated_hours_auto || 0}h estimated`}
              color="#10B981"
            />
            <KPI
              label={lang === 'es' ? 'Revision Manual' : 'Manual Review'}
              value={t.manual_review?.toLocaleString() || '0'}
              color="#F59E0B"
            />
            <KPI
              label={lang === 'es' ? 'Dias Est. (4 devs)' : 'Est. Days (4 devs)'}
              value={t.estimated_days_4dev || '0'}
              subtitle={`${t.estimated_hours_total || 0}h total`}
              color="#6366F1"
            />
            <KPI
              label="PII Critical"
              value={p.critical || '0'}
              subtitle={`${p.total || 0} total PII`}
              color="#DC2626"
            />
          </div>

          {/* Two-column layout */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
            gap: 20, marginBottom: 24,
          }}>
            {/* Risk Overview */}
            <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #E5E7EB', padding: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#111827', marginBottom: 16 }}>
                {lang === 'es' ? 'Exposicion de Riesgo' : 'Risk Exposure'}
              </h3>

              <RiskMeter
                score={t.critical || 0}
                maxScore={t.total_issues || 1}
                label={lang === 'es' ? 'Issues Criticos' : 'Critical Issues'}
              />
              <RiskMeter
                score={p.critical || 0}
                maxScore={p.total || 1}
                label={lang === 'es' ? 'PII Critico' : 'Critical PII'}
              />
              <RiskMeter
                score={100 - parseFloat(d.fk_coverage || '0')}
                maxScore={100}
                label={lang === 'es' ? 'DB Sin Foreign Keys' : 'DB Missing FK'}
              />

              {/* Severity distribution bar */}
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', marginBottom: 6 }}>
                  {lang === 'es' ? 'Distribucion por Severidad' : 'Severity Distribution'}
                </div>
                <SeverityBar data={triageData.by_severity || {}} />
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  {Object.entries(triageData.by_severity || {}).map(([sev, count]) => (
                    <div key={sev} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
                      <div style={{ width: 8, height: 8, borderRadius: 2, background: SEVERITY_COLORS[sev] }} />
                      <span style={{ color: '#6B7280' }}>{sev}: {count.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Categories breakdown */}
            <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #E5E7EB', padding: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#111827', marginBottom: 16 }}>
                {lang === 'es' ? 'Issues por Categoria' : 'Issues by Category'}
              </h3>
              {Object.entries(triageData.by_category || {})
                .sort((a, b) => b[1] - a[1])
                .slice(0, 8)
                .map(([cat, count]) => {
                  const info = CATEGORY_ICONS[cat] || { icon: '📌', label: cat }
                  const pct = ((count / (t.total_issues || 1)) * 100).toFixed(1)
                  return (
                    <div key={cat} style={{
                      display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10,
                    }}>
                      <span style={{ fontSize: 18 }}>{info.icon}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                          <span style={{ fontSize: 13, fontWeight: 500, color: '#374151' }}>{info.label}</span>
                          <span style={{ fontSize: 12, color: '#6B7280' }}>{count.toLocaleString()} ({pct}%)</span>
                        </div>
                        <div style={{ height: 4, background: '#F3F4F6', borderRadius: 2 }}>
                          <div style={{
                            height: '100%', width: `${pct}%`, background: '#6366F1',
                            borderRadius: 2, minWidth: 2,
                          }} />
                        </div>
                      </div>
                    </div>
                  )
                })}
            </div>
          </div>

          {/* Remediation Timeline */}
          <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #E5E7EB', padding: 20, marginBottom: 24 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#111827', marginBottom: 16 }}>
              {lang === 'es' ? 'Plan de Remediacion' : 'Remediation Plan'}
            </h3>
            <BatchTimeline batches={triageData.batches || []} lang={lang} />
          </div>

          {/* PII Detail */}
          {piiData && piiData.by_type && Object.keys(piiData.by_type).length > 0 && (
            <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #E5E7EB', padding: 20, marginBottom: 24 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#DC2626', marginBottom: 16 }}>
                {lang === 'es' ? 'Exposicion de Datos Personales' : 'Personal Data Exposure'}
              </h3>
              <div style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)',
                gap: 12,
              }}>
                {Object.entries(piiData.by_type).map(([type, count]) => (
                  <div key={type} style={{
                    padding: 14, borderRadius: 10, border: '1px solid #FEE2E2',
                    background: '#FFF5F5',
                  }}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: '#DC2626' }}>{count}</div>
                    <div style={{ fontSize: 13, color: '#9B2C2C', fontWeight: 500 }}>{type.replace(/_/g, ' ')}</div>
                  </div>
                ))}
              </div>

              {piiData.recommendations && piiData.recommendations.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
                    {lang === 'es' ? 'Acciones Recomendadas' : 'Recommended Actions'}
                  </div>
                  {piiData.recommendations.map((rec, i) => (
                    <div key={i} style={{
                      padding: 10, marginBottom: 6, borderRadius: 8,
                      background: rec.priority === 'P0' ? '#FEF2F2' : '#FFF7ED',
                      border: `1px solid ${rec.priority === 'P0' ? '#FECACA' : '#FED7AA'}`,
                      fontSize: 13,
                    }}>
                      <span style={{
                        fontWeight: 700, marginRight: 8,
                        color: rec.priority === 'P0' ? '#DC2626' : '#D97706',
                      }}>
                        [{rec.priority}]
                      </span>
                      <span style={{ color: '#374151' }}>{rec.title}</span>
                      <span style={{ color: '#9CA3AF', marginLeft: 8 }}>{rec.effort}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Financial Impact */}
          <div style={{
            background: 'linear-gradient(135deg, #1E1B4B, #312E81)', borderRadius: 14,
            padding: 24, color: '#fff', marginBottom: 24,
          }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, color: '#C7D2FE' }}>
              {lang === 'es' ? 'Impacto Financiero Estimado' : 'Estimated Financial Impact'}
            </h3>
            <div style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)',
              gap: 16,
            }}>
              <div>
                <div style={{ fontSize: 12, color: '#A5B4FC' }}>
                  {lang === 'es' ? 'Riesgo Reputacional' : 'Reputational Risk'}
                </div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>$13M USD</div>
                <div style={{ fontSize: 11, color: '#818CF8' }}>Public-market exposure</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#A5B4FC' }}>
                  {lang === 'es' ? 'Penalidad Datos' : 'Data Penalty'}
                </div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>$5M USD</div>
                <div style={{ fontSize: 11, color: '#818CF8' }}>GDPR-level PII</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#A5B4FC' }}>
                  {lang === 'es' ? 'Ahorro Auto-Fix' : 'Auto-Fix Savings'}
                </div>
                <div style={{ fontSize: 24, fontWeight: 800, color: '#34D399' }}>
                  {t.estimated_hours_auto || 0}h
                </div>
                <div style={{ fontSize: 11, color: '#818CF8' }}>
                  ~${((t.estimated_hours_auto || 0) * 75).toLocaleString()} USD saved
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Empty state */}
      {!triageData && !loading && (
        <div style={{ textAlign: 'center', padding: 60, color: '#9CA3AF' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📊</div>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>
            {lang === 'es' ? 'Sin datos de analisis' : 'No analysis data'}
          </div>
          <div style={{ fontSize: 14 }}>
            {lang === 'es'
              ? 'Ingresa la ruta de un repositorio para generar el panel ejecutivo.'
              : 'Enter a repository path to generate the executive dashboard.'}
          </div>
        </div>
      )}
    </div>
  )
}
