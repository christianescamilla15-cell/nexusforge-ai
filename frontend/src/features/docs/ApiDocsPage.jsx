import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

export default function ApiDocsPage({ lang = 'en' }) {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    fetchAPI('/health').then(res => { if (res.data) setHealth(res.data) })
  }, [])

  const card = {
    background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
    padding: 20, marginBottom: 16,
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out', maxWidth: 640 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
        {lang === 'es' ? 'Documentacion API' : 'API Documentation'}
      </h1>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 24 }}>
        {lang === 'es' ? 'Referencia completa de endpoints, schemas, y autenticacion.' : 'Complete reference for endpoints, schemas, and authentication.'}
      </p>

      <div style={card}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: '#111827', marginBottom: 10 }}>
          {lang === 'es' ? 'Autenticacion' : 'Authentication'}
        </h3>
        <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.7 }}>
          <p><strong>JWT Token:</strong> POST /api/auth/login → <code style={{ background: '#F3F4F6', padding: '2px 6px', borderRadius: 4 }}>Authorization: Bearer {'<token>'}</code></p>
          <p><strong>API Key:</strong> POST /api/api-keys/generate → <code style={{ background: '#F3F4F6', padding: '2px 6px', borderRadius: 4 }}>X-API-Key: {'<key>'}</code></p>
        </div>
      </div>

      <div style={card}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: '#111827', marginBottom: 10 }}>
          {lang === 'es' ? 'Endpoints principales' : 'Main Endpoints'}
        </h3>
        <div style={{ fontSize: 12, fontFamily: 'monospace', lineHeight: 2, color: '#374151' }}>
          {[
            'POST /api/auth/register', 'POST /api/auth/login',
            'GET  /api/automations', 'POST /api/automations/{id}/run',
            'GET  /api/workflows', 'POST /api/executions',
            'GET  /api/agents', 'POST /api/swarms/execute',
            'POST /api/wizard/generate', 'POST /api/wizard/chat',
            'GET  /api/health', 'GET  /api/runs/reliability/health',
          ].map(ep => <div key={ep}>{ep}</div>)}
        </div>
      </div>

      {health && (
        <div style={{ fontSize: 12, color: '#D1D5DB', textAlign: 'center' }}>
          API: {health.status} &middot; {health.agent_count} agents &middot; {health.migrations_applied} migrations
        </div>
      )}
    </div>
  )
}
