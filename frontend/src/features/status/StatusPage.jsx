import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

const T = {
  en: { title: 'System Status', subtitle: 'Real-time health of all NexusForge components.', healthy: 'Healthy', degraded: 'Degraded', down: 'Down', agents: 'Agents', migrations: 'Migrations', refresh: 'Refresh', lastCheck: 'Last check' },
  es: { title: 'Estado del Sistema', subtitle: 'Salud en tiempo real de todos los componentes.', healthy: 'Saludable', degraded: 'Degradado', down: 'Caido', agents: 'Agentes', migrations: 'Migraciones', refresh: 'Refrescar', lastCheck: 'Ultima verificacion' },
}

const STATUS_COLOR = { up: '#10B981', down: '#EF4444', healthy: '#10B981', degraded: '#F59E0B' }

export default function StatusPage({ lang = 'en' }) {
  const t = T[lang] || T.en
  const [health, setHealth] = useState(null)
  const [providers, setProviders] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastCheck, setLastCheck] = useState(null)
  const [error, setError] = useState(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    const [hRes, pRes] = await Promise.all([
      fetchAPI('/health'),
      fetchAPI('/providers/status'),
    ])
    if (hRes.error) { setError(hRes.error); setLoading(false); return }
    if (hRes.data) setHealth(hRes.data)
    if (pRes.data) setProviders(pRes.data)
    setLastCheck(new Date().toLocaleTimeString())
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [])

  const statusDot = (status) => (
    <span style={{
      width: 10, height: 10, borderRadius: '50%', display: 'inline-block',
      background: STATUS_COLOR[status] || STATUS_COLOR.down,
    }} />
  )

  const card = {
    background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
    padding: 20, marginBottom: 16,
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out', maxWidth: 640 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>{t.title}</h1>
          <p style={{ fontSize: 14, color: '#9CA3AF' }}>{t.subtitle}</p>
        </div>
        <button onClick={load} disabled={loading} style={{
          padding: '8px 16px', borderRadius: 8, border: '1px solid #E5E7EB',
          background: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer', color: '#6B7280',
        }}>{loading ? '...' : t.refresh}</button>
      </div>

      {error && <div style={{ padding: 12, borderRadius: 8, background: '#FEE2E2', color: '#DC2626', fontSize: 13, marginBottom: 16 }}>{error}</div>}

      {health && (
        <>
          {/* Overall status */}
          <div style={{
            ...card,
            borderColor: STATUS_COLOR[health.status] || '#E5E7EB',
            background: `${STATUS_COLOR[health.status] || '#F9FAFB'}08`,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              {statusDot(health.status)}
              <span style={{ fontSize: 18, fontWeight: 700, color: '#111827', textTransform: 'capitalize' }}>
                {health.status === 'healthy' ? t.healthy : t.degraded}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 20, fontSize: 13, color: '#6B7280' }}>
              <span>{t.agents}: <strong>{health.agent_count}</strong></span>
              <span>{t.migrations}: <strong>{health.migrations_applied}</strong></span>
            </div>
          </div>

          {/* Components */}
          <div style={card}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 14 }}>
              {lang === 'es' ? 'Componentes' : 'Components'}
            </h3>
            {Object.entries(health.components || {}).map(([name, status]) => (
              <div key={name} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 0', borderBottom: '1px solid #F3F4F6',
              }}>
                <span style={{ fontSize: 14, color: '#374151', textTransform: 'capitalize' }}>{name}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {statusDot(typeof status === 'string' && status.startsWith('down') ? 'down' : 'up')}
                  <span style={{
                    fontSize: 12, fontWeight: 600,
                    color: typeof status === 'string' && status.startsWith('down') ? '#EF4444' : '#10B981',
                  }}>
                    {typeof status === 'string' && status.startsWith('down') ? t.down : 'Up'}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Agent Health */}
          {health.agent_health && Object.keys(health.agent_health).length > 0 && (
            <div style={card}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 14 }}>
                {lang === 'es' ? 'Salud de Agentes' : 'Agent Health'}
              </h3>
              {Object.entries(health.agent_health).map(([name, info]) => (
                <div key={name} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '8px 0', borderBottom: '1px solid #F3F4F6', fontSize: 13,
                }}>
                  <span style={{ color: '#374151' }}>{name}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ color: '#9CA3AF' }}>
                      {Math.round((info.health_score || 0) * 100)}%
                    </span>
                    <div style={{ width: 60, height: 4, background: '#E5E7EB', borderRadius: 2 }}>
                      <div style={{
                        height: '100%', borderRadius: 2,
                        width: `${(info.health_score || 0) * 100}%`,
                        background: (info.health_score || 0) > 0.7 ? '#10B981' : (info.health_score || 0) > 0.4 ? '#F59E0B' : '#EF4444',
                      }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* LLM Providers */}
          {providers && (
            <div style={card}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 14 }}>
                {lang === 'es' ? 'Proveedores LLM' : 'LLM Providers'}
              </h3>
              {Object.entries(providers.providers || providers).map(([name, info]) => (
                <div key={name} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '8px 0', borderBottom: '1px solid #F3F4F6', fontSize: 13,
                }}>
                  <span style={{ color: '#374151', textTransform: 'capitalize' }}>{name}</span>
                  <span style={{
                    padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                    background: info.configured || info.available ? '#DCFCE7' : '#FEE2E2',
                    color: info.configured || info.available ? '#166534' : '#991B1B',
                  }}>
                    {info.configured || info.available ? 'Active' : 'Not configured'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {lastCheck && (
        <p style={{ fontSize: 12, color: '#D1D5DB', textAlign: 'center' }}>
          {t.lastCheck}: {lastCheck}
        </p>
      )}
    </div>
  )
}
