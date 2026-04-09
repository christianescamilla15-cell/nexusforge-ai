import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'
import { useIsMobile } from '../../shared/hooks/useIsMobile'

function KPI({ label, value, sub, color }) {
  return (
    <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 16 }}>
      <div style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 800, color: color || '#111827' }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

export default function AdminDashboard({ lang = 'es' }) {
  const isMobile = useIsMobile()
  const [data, setData] = useState(null)
  const [users, setUsers] = useState(null)
  const [usage, setUsage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState('overview')

  useEffect(() => {
    async function load() {
      setLoading(true)
      const [dRes, uRes, usRes] = await Promise.all([
        fetchAPI('/admin/dashboard'),
        fetchAPI('/admin/users?limit=20'),
        fetchAPI('/admin/usage?days=30'),
      ])
      if (dRes.error && dRes.error.includes('Not found')) {
        setError(lang === 'es' ? 'Acceso denegado — solo administradores' : 'Access denied — admins only')
      } else {
        if (dRes.data) setData(dRes.data)
        if (uRes.data) setUsers(uRes.data)
        if (usRes.data) setUsage(usRes.data)
      }
      setLoading(false)
    }
    load()
  }, [lang])

  const handleSearch = async () => {
    const res = await fetchAPI(`/admin/users?search=${encodeURIComponent(search)}&limit=50`)
    if (res.data) setUsers(res.data)
  }

  const handleSuspend = async (userId) => {
    await fetchAPI(`/admin/users/${userId}/suspend`, { method: 'POST' })
    handleSearch()
  }

  const handleActivate = async (userId) => {
    await fetchAPI(`/admin/users/${userId}/activate`, { method: 'POST' })
    handleSearch()
  }

  if (loading) return <div style={{ padding: 32, color: '#9CA3AF' }}>Loading admin panel...</div>
  if (error) return (
    <div style={{ padding: 32, textAlign: 'center' }}>
      <div style={{ fontSize: 48, marginBottom: 12 }}>🔒</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: '#DC2626' }}>{error}</div>
    </div>
  )

  const d = data || {}
  const u = d.users || {}
  const r = d.runs || {}
  const a = d.automations || {}
  const o = d.organizations || {}

  const tabs = [
    { key: 'overview', label: lang === 'es' ? 'General' : 'Overview' },
    { key: 'users', label: lang === 'es' ? 'Usuarios' : 'Users' },
    { key: 'usage', label: lang === 'es' ? 'Uso' : 'Usage' },
    { key: 'errors', label: lang === 'es' ? 'Errores' : 'Errors' },
  ]

  return (
    <div style={{ padding: isMobile ? 16 : 32, maxWidth: 1400, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 800, color: '#111827', marginBottom: 4 }}>
        {lang === 'es' ? 'Panel de Administracion' : 'Admin Panel'}
      </h1>
      <p style={{ fontSize: 13, color: '#9CA3AF', marginBottom: 20 }}>
        {lang === 'es' ? 'Gestion del sistema, usuarios y organizaciones.' : 'System, user, and organization management.'}
      </p>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid #E5E7EB', paddingBottom: 0 }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '8px 16px', border: 'none', borderBottom: tab === t.key ? '2px solid #6366F1' : '2px solid transparent',
            background: 'none', color: tab === t.key ? '#6366F1' : '#9CA3AF',
            fontWeight: tab === t.key ? 700 : 400, fontSize: 14, cursor: 'pointer',
          }}>{t.label}</button>
        ))}
      </div>

      {/* Overview Tab */}
      {tab === 'overview' && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(2,1fr)' : 'repeat(5,1fr)', gap: 12, marginBottom: 20 }}>
            <KPI label={lang === 'es' ? 'Usuarios' : 'Users'} value={u.total || 0} sub={`${u.active || 0} activos`} />
            <KPI label={lang === 'es' ? 'Organizaciones' : 'Organizations'} value={o.total || 0} sub={`${o.paying || 0} pagando`} color="#6366F1" />
            <KPI label={lang === 'es' ? 'Ejecuciones' : 'Runs'} value={r.total || 0} sub={`${r.last_24h || 0} ultimas 24h`} />
            <KPI label="Tokens" value={(r.total_tokens || 0).toLocaleString()} sub={`$${(r.total_cost_usd || 0).toFixed(2)}`} color="#10B981" />
            <KPI label={lang === 'es' ? 'Automatizaciones' : 'Automations'} value={a.total || 0} sub={`${a.active || 0} activas`} />
          </div>

          {/* Plan distribution */}
          {d.plans && (
            <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 16, marginBottom: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginBottom: 12 }}>
                {lang === 'es' ? 'Distribucion de Planes' : 'Plan Distribution'}
              </div>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                {Object.entries(d.plans).map(([plan, count]) => (
                  <div key={plan} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: plan === 'free' ? '#9CA3AF' : '#6366F1' }}>{count}</div>
                    <div style={{ fontSize: 12, color: '#6B7280', textTransform: 'capitalize' }}>{plan}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* New users */}
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
              {lang === 'es' ? 'Crecimiento' : 'Growth'}
            </div>
            <div style={{ display: 'flex', gap: 24 }}>
              <div><span style={{ fontSize: 18, fontWeight: 700 }}>{u.new_7d || 0}</span> <span style={{ fontSize: 12, color: '#6B7280' }}>7 dias</span></div>
              <div><span style={{ fontSize: 18, fontWeight: 700 }}>{u.new_30d || 0}</span> <span style={{ fontSize: 12, color: '#6B7280' }}>30 dias</span></div>
            </div>
          </div>
        </>
      )}

      {/* Users Tab */}
      {tab === 'users' && users && (
        <>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <input value={search} onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder={lang === 'es' ? 'Buscar por email o nombre...' : 'Search by email or name...'}
              style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #D1D5DB', fontSize: 14 }}
            />
            <button onClick={handleSearch} style={{
              padding: '8px 16px', borderRadius: 8, border: 'none',
              background: '#6366F1', color: '#fff', fontWeight: 600, cursor: 'pointer',
            }}>{lang === 'es' ? 'Buscar' : 'Search'}</button>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #E5E7EB' }}>
                  <th style={{ textAlign: 'left', padding: 8, color: '#6B7280' }}>Email</th>
                  <th style={{ padding: 8, color: '#6B7280' }}>Plan</th>
                  <th style={{ padding: 8, color: '#6B7280' }}>Runs</th>
                  <th style={{ padding: 8, color: '#6B7280' }}>Tokens</th>
                  <th style={{ padding: 8, color: '#6B7280' }}>Status</th>
                  <th style={{ padding: 8, color: '#6B7280' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {(users.users || []).map(u => (
                  <tr key={u.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                    <td style={{ padding: 8 }}>
                      <div style={{ fontWeight: 500 }}>{u.email}</div>
                      <div style={{ fontSize: 11, color: '#9CA3AF' }}>{u.name}</div>
                    </td>
                    <td style={{ padding: 8, textAlign: 'center' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                        background: u.plan === 'free' ? '#F3F4F6' : '#EEF2FF',
                        color: u.plan === 'free' ? '#6B7280' : '#6366F1',
                      }}>{u.plan}</span>
                    </td>
                    <td style={{ padding: 8, textAlign: 'center' }}>{u.total_runs}</td>
                    <td style={{ padding: 8, textAlign: 'center' }}>{u.total_tokens.toLocaleString()}</td>
                    <td style={{ padding: 8, textAlign: 'center' }}>
                      <span style={{
                        width: 8, height: 8, borderRadius: '50%', display: 'inline-block',
                        background: u.is_active ? '#10B981' : '#EF4444',
                      }} />
                    </td>
                    <td style={{ padding: 8, textAlign: 'center' }}>
                      {u.is_active ? (
                        <button onClick={() => handleSuspend(u.id)} style={{
                          padding: '4px 10px', borderRadius: 4, border: '1px solid #FECACA',
                          background: '#FFF5F5', color: '#DC2626', fontSize: 11, cursor: 'pointer',
                        }}>Suspend</button>
                      ) : (
                        <button onClick={() => handleActivate(u.id)} style={{
                          padding: '4px 10px', borderRadius: 4, border: '1px solid #D1FAE5',
                          background: '#F0FFF4', color: '#059669', fontSize: 11, cursor: 'pointer',
                        }}>Activate</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 8 }}>
            {users.total || 0} {lang === 'es' ? 'usuarios totales' : 'total users'}
          </div>
        </>
      )}

      {/* Usage Tab */}
      {tab === 'usage' && usage && (
        <>
          {/* Top users */}
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 16, marginBottom: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginBottom: 12 }}>
              Top Users (30 days)
            </div>
            {(usage.top_users || []).map((u, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #F3F4F6' }}>
                <span style={{ fontSize: 13 }}>{u.email} <span style={{ fontSize: 11, color: '#9CA3AF' }}>({u.plan})</span></span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{u.tokens.toLocaleString()} tokens / ${u.cost.toFixed(2)}</span>
              </div>
            ))}
          </div>

          {/* Daily chart (simple text) */}
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginBottom: 12 }}>
              {lang === 'es' ? 'Actividad Diaria' : 'Daily Activity'}
            </div>
            <div style={{ overflowX: 'auto', maxHeight: 300 }}>
              {(usage.daily || []).slice(-14).map((d, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 12 }}>
                  <span style={{ color: '#6B7280', minWidth: 80 }}>{d.date}</span>
                  <span>{d.runs} runs</span>
                  <span>{d.tokens.toLocaleString()} tok</span>
                  <span style={{ color: '#10B981' }}>${d.cost.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Errors Tab */}
      {tab === 'errors' && (
        <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#DC2626', marginBottom: 12 }}>
            {lang === 'es' ? 'Errores Recientes (24h)' : 'Recent Errors (24h)'}
          </div>
          {(d.recent_errors || []).length === 0 ? (
            <div style={{ color: '#10B981', fontSize: 14 }}>
              {lang === 'es' ? 'Sin errores en las ultimas 24 horas' : 'No errors in the last 24 hours'}
            </div>
          ) : (
            (d.recent_errors || []).map((e, i) => (
              <div key={i} style={{
                padding: 10, marginBottom: 6, borderRadius: 8,
                background: '#FEF2F2', border: '1px solid #FECACA', fontSize: 13,
              }}>
                <span style={{ color: '#DC2626', fontWeight: 600, marginRight: 8 }}>{e.id.slice(0, 8)}</span>
                <span style={{ color: '#374151' }}>{e.error}</span>
                <span style={{ color: '#9CA3AF', marginLeft: 8, fontSize: 11 }}>{e.created_at}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
