import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

const TIERS = [
  {
    name: 'Working Memory',
    key: 'working',
    storage: 'In-Memory (Dict)',
    ttl: 'Per-execution',
    color: '#60A5FA',
    bg: 'rgba(96,165,250,0.12)',
    border: 'rgba(96,165,250,0.2)',
    icon: 'M12 6v6l4 2',
    desc: 'Datos temporales de la ejecucion actual. Se elimina al completar la tarea.',
  },
  {
    name: 'Episodic Memory',
    key: 'episodic',
    storage: 'Redis + MongoDB',
    ttl: '30 dias',
    color: '#F59E0B',
    bg: 'rgba(245,158,11,0.12)',
    border: 'rgba(245,158,11,0.2)',
    icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
    desc: 'Historial de ejecuciones recientes. Permite aprender de errores anteriores.',
  },
  {
    name: 'Semantic Memory',
    key: 'semantic',
    storage: 'PostgreSQL + pgvector',
    ttl: 'Permanente',
    color: '#10B981',
    bg: 'rgba(16,185,129,0.12)',
    border: 'rgba(16,185,129,0.2)',
    icon: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4',
    desc: 'Conocimiento permanente con embeddings. Busqueda semantica por similaridad.',
  },
]

export default function MemoryPanel({ agentType, lang = 'es' }) {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!agentType) { setLoading(false); return }
    fetchAPI(`/memory/stats/${agentType}`).then(res => {
      if (!res.error && res.data) setStats(res.data)
      setLoading(false)
    })
  }, [agentType])

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          {lang === 'es' ? 'Sistema de Memoria 5-Tier' : '5-Tier Memory System'}
        </h2>
        <p style={{ fontSize: 13, color: '#9CA3AF' }}>
          {lang === 'es'
            ? 'Los datos fluyen de Working a Episodic al completar tareas, y a Semantic cuando se detectan patrones persistentes.'
            : 'Data flows from Working to Episodic on task completion, and to Semantic when persistent patterns are detected.'}
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {TIERS.map((tier, idx) => {
          const count = stats?.[tier.key] ?? null
          return (
            <div key={tier.name}>
              <div
                aria-label={`Tier de memoria: ${tier.name}`}
                style={{
                  background: '#FFFFFF',
                  border: `1px solid ${tier.border}`,
                  borderRadius: 12,
                  padding: 20,
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.boxShadow = `0 0 16px ${tier.border}` }}
                onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'none' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{
                    width: 40, height: 40, borderRadius: 10, background: tier.bg,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                      stroke={tier.color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d={tier.icon} />
                    </svg>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 15, fontWeight: 600, color: tier.color }}>{tier.name}</div>
                    <div style={{ fontSize: 12, color: '#9CA3AF' }}>{tier.desc}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 11, color: '#9CA3AF' }}>Storage</div>
                    <div style={{ fontSize: 12, fontWeight: 500, color: '#111827' }}>{tier.storage}</div>
                  </div>
                  <div style={{ textAlign: 'right', marginLeft: 12 }}>
                    <div style={{ fontSize: 11, color: '#9CA3AF' }}>TTL</div>
                    <div style={{ fontSize: 12, fontWeight: 500, color: tier.color }}>{tier.ttl}</div>
                  </div>
                  {count !== null && (
                    <div style={{ textAlign: 'right', marginLeft: 12 }}>
                      <div style={{ fontSize: 11, color: '#9CA3AF' }}>Entries</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: tier.color }}>{count}</div>
                    </div>
                  )}
                </div>

                {loading && (
                  <div style={{ marginTop: 8, fontSize: 12, color: '#9CA3AF' }}>
                    {lang === 'es' ? 'Cargando...' : 'Loading...'}
                  </div>
                )}
              </div>

              {idx < TIERS.length - 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0' }}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M12 5v14M12 19l-4-4M12 19l4-4" stroke="#4B5563" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
