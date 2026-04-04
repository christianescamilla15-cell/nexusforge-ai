import { useState, useEffect } from 'react'
import { t } from '../../shared/i18n/translations'
import { fetchAPI } from '../../services/api'

export default function HealingPage({ lang = 'en', embedded = false }) {
  const [realStats, setRealStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 900)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchAPI('/healing/stats').then(res => {
      if (!res.error && res.data) setRealStats(res.data)
      setLoading(false)
    })
  }, [])

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Header */}
      {!embedded && (
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
            {t('selfHealing', lang)}
          </h1>
          <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
            {lang === 'es'
              ? 'Estadisticas del sistema de auto-reparacion: fallos detectados, reparados y pendientes.'
              : 'Self-healing system stats: detected failures, healed, and pending.'}
          </p>
        </div>
      )}

      {loading && (
        <div style={{ padding: 32, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
          {lang === 'es' ? 'Cargando estadisticas...' : 'Loading stats...'}
        </div>
      )}

      {!loading && !realStats && (
        <div style={{
          padding: 32, textAlign: 'center', borderRadius: 12,
          border: '1px solid #E5E7EB', background: '#fff',
        }}>
          <span style={{ fontSize: 32, display: 'block', marginBottom: 8 }}>🛡️</span>
          <p style={{ fontSize: 14, color: '#6B7280', margin: 0 }}>
            {lang === 'es'
              ? 'No se pudieron cargar las estadisticas de healing. Verifica que el backend este corriendo.'
              : 'Could not load healing stats. Verify that the backend is running.'}
          </p>
        </div>
      )}

      {/* Real backend stats */}
      {realStats && (
        <>
          <div style={{
            display: 'grid', gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
            gap: 12, marginBottom: 20,
          }}>
            {[
              { label: lang === 'es' ? 'Fallos totales' : 'Total failures', value: realStats.total_failures, color: '#EF4444', bg: 'rgba(239,68,68,0.08)' },
              { label: lang === 'es' ? 'Reparados' : 'Healed', value: realStats.total_healed, color: '#10B981', bg: 'rgba(16,185,129,0.08)' },
              { label: lang === 'es' ? 'Tasa de curacion' : 'Heal rate', value: `${realStats.heal_rate}%`, color: '#6366F1', bg: 'rgba(99,102,241,0.08)' },
              { label: lang === 'es' ? 'Dead letters' : 'Dead letters', value: realStats.dead_letters, color: '#F59E0B', bg: 'rgba(245,158,11,0.08)' },
            ].map(s => (
              <div key={s.label} style={{
                padding: '14px 16px', borderRadius: 10, background: s.bg,
                border: `1px solid ${s.color}33`,
              }}>
                <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4 }}>{s.label}</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
              </div>
            ))}
          </div>

          {/* Recent real failures */}
          {realStats.recent_failures?.length > 0 && (
            <div style={{
              background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
              padding: 16,
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#111827', marginBottom: 10 }}>
                {lang === 'es' ? 'Fallos recientes' : 'Recent failures'}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {realStats.recent_failures.slice(0, 10).map((f, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 10, fontSize: 12,
                    padding: '6px 10px', borderRadius: 8, background: '#FEF2F2',
                  }}>
                    <span style={{ color: '#EF4444', fontWeight: 600, minWidth: 80 }}>{f.agent_type}</span>
                    <span style={{ color: '#6B7280', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {f.step_name} — {f.error_message || 'unknown error'}
                    </span>
                    {f.retry_count > 0 && (
                      <span style={{ color: '#9CA3AF', whiteSpace: 'nowrap' }}>x{f.retry_count}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {realStats.recent_failures?.length === 0 && (
            <div style={{
              padding: 24, textAlign: 'center', borderRadius: 12,
              border: '1px solid #E5E7EB', background: '#F0FDF4',
            }}>
              <span style={{ fontSize: 24, display: 'block', marginBottom: 8 }}>✅</span>
              <p style={{ fontSize: 13, color: '#16A34A', margin: 0 }}>
                {lang === 'es' ? 'Sin fallos recientes. El sistema esta saludable.' : 'No recent failures. System is healthy.'}
              </p>
            </div>
          )}
        </>
      )}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
