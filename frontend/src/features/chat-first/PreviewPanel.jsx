import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'
import { usePreviewEvents } from './hooks/usePreviewEvents'
import PreviewRenderer from './PreviewRenderer'

/**
 * Right panel — shows live preview of what's being built.
 * When idle, shows mini KPI dashboard.
 */
export default function PreviewPanel({ lang = 'es' }) {
  const { previewState, stepStatuses } = usePreviewEvents()
  const [kpis, setKpis] = useState(null)

  // Fetch KPIs for the mini dashboard
  useEffect(() => {
    fetchAPI('/runs/reliability/health').then(res => {
      if (!res.error && res.data) setKpis(res.data)
    }).catch(() => {})
  }, [])

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: '#fff', borderLeft: '1px solid #E5E7EB',
    }}>
      {/* Mini KPI strip at top */}
      {kpis && (
        <div style={{
          padding: '12px 16px', borderBottom: '1px solid #F3F4F6',
          display: 'flex', gap: 12,
        }}>
          {[
            { value: kpis.total_runs ?? 0, label: lang === 'es' ? 'Ejecuciones' : 'Runs', color: '#6366F1' },
            {
              value: kpis.system_success_rate != null ? `${(kpis.system_success_rate * 100).toFixed(0)}%` : '--',
              label: lang === 'es' ? '\u00C9xito' : 'Success',
              color: '#059669',
            },
            { value: kpis.total_agents_tracked ?? 0, label: lang === 'es' ? 'Agentes' : 'Agents', color: '#D97706' },
          ].map(kpi => (
            <div key={kpi.label} style={{
              flex: 1, padding: '8px 10px', borderRadius: 10,
              background: `${kpi.color}08`, textAlign: 'center',
            }}>
              <div style={{ fontSize: 18, fontWeight: 800, color: kpi.color }}>
                {kpi.value}
              </div>
              <div style={{ fontSize: 10, color: '#9CA3AF', marginTop: 2 }}>
                {kpi.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Preview content */}
      <div style={{
        flex: 1, overflow: 'auto',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{ width: '100%', maxWidth: 400 }}>
          <PreviewRenderer previewState={previewState} stepStatuses={stepStatuses} lang={lang} />
        </div>
      </div>

      {/* Footer */}
      <div style={{
        padding: '10px 16px', borderTop: '1px solid #F3F4F6',
        textAlign: 'center', fontSize: 11, color: '#C4B5FD',
      }}>
        NexusForge AI &mdash; {lang === 'es' ? 'Vista previa en vivo' : 'Live preview'}
      </div>
    </div>
  )
}
