import { useState } from 'react'
import { api } from '../../api/client'

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState(
    () => (typeof window !== 'undefined' && import.meta.env.VITE_API_URL) || 'http://localhost:8000/api'
  )
  const [language, setLanguage] = useState('es')
  const [darkMode] = useState(true)
  const [healthResult, setHealthResult] = useState(null)
  const [healthLoading, setHealthLoading] = useState(false)

  const checkHealth = async () => {
    setHealthLoading(true)
    setHealthResult(null)
    try {
      const data = await api.get('/health')
      setHealthResult({ ok: true, data })
    } catch (err) {
      setHealthResult({ ok: false, error: err.message || 'No se pudo conectar' })
    } finally {
      setHealthLoading(false)
    }
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out', maxWidth: 640 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 4 }}>Ajustes</h1>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 32 }}>
        Configura las preferencias del sistema NexusForge.
      </p>

      {/* Settings cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* API URL */}
        <div style={cardStyle}>
          <div style={{ marginBottom: 12 }}>
            <label style={labelStyle}>API Base URL</label>
            <p style={descStyle}>URL del servidor backend de NexusForge.</p>
          </div>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            aria-label="API Base URL"
            style={inputStyle}
            onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
            onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
          />
        </div>

        {/* Theme */}
        <div style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <label style={labelStyle}>Tema</label>
              <p style={descStyle}>Dark mode esta activado. Otros temas proximamente.</p>
            </div>
            <div style={{
              width: 44, height: 24, borderRadius: 12, padding: 2,
              background: darkMode ? '#6366F1' : 'rgba(255,255,255,0.1)',
              opacity: 0.5, cursor: 'not-allowed', transition: 'background 0.2s',
            }}>
              <div style={{
                width: 20, height: 20, borderRadius: '50%', background: '#fff',
                transform: darkMode ? 'translateX(20px)' : 'translateX(0)',
                transition: 'transform 0.2s',
              }} />
            </div>
          </div>
        </div>

        {/* Language */}
        <div style={cardStyle}>
          <div style={{ marginBottom: 12 }}>
            <label style={labelStyle}>Idioma</label>
            <p style={descStyle}>Selecciona el idioma de la interfaz.</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {[
              { key: 'es', label: 'Espanol' },
              { key: 'en', label: 'English' },
            ].map((lang) => (
              <button
                key={lang.key}
                onClick={() => setLanguage(lang.key)}
                aria-label={`Idioma ${lang.label}`}
                style={{
                  padding: '8px 20px', borderRadius: 8, border: 'none', fontSize: 14,
                  fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s',
                  background: language === lang.key ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.04)',
                  color: language === lang.key ? '#818CF8' : '#9CA3AF',
                }}
              >
                {lang.label}
              </button>
            ))}
          </div>
        </div>

        {/* Health Check */}
        <div style={cardStyle}>
          <div style={{ marginBottom: 12 }}>
            <label style={labelStyle}>Estado del API</label>
            <p style={descStyle}>Verifica la conexion con el backend.</p>
          </div>
          <button
            onClick={checkHealth}
            disabled={healthLoading}
            aria-label="Verificar estado del API"
            style={{
              padding: '10px 24px', borderRadius: 8, border: 'none',
              background: healthLoading ? 'rgba(99,102,241,0.3)' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              color: '#fff', fontSize: 14, fontWeight: 600,
              cursor: healthLoading ? 'not-allowed' : 'pointer',
              marginBottom: healthResult ? 12 : 0,
            }}
          >
            {healthLoading ? 'Verificando...' : 'Verificar Conexion'}
          </button>
          {healthResult && (
            <div style={{
              padding: '12px 16px', borderRadius: 8,
              background: healthResult.ok ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
              border: `1px solid ${healthResult.ok ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
              color: healthResult.ok ? '#10B981' : '#EF4444',
              fontSize: 13,
            }}>
              {healthResult.ok
                ? `API operativo: ${JSON.stringify(healthResult.data)}`
                : `Error: ${healthResult.error}`
              }
            </div>
          )}
        </div>

        {/* Version */}
        <div style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <label style={labelStyle}>Version</label>
              <p style={descStyle}>NexusForge AI Platform</p>
            </div>
            <span style={{
              fontSize: 14, fontWeight: 600, color: '#6366F1',
              fontFamily: 'monospace',
            }}>v1.0.0</span>
          </div>
        </div>

      </div>
    </div>
  )
}

const cardStyle = {
  background: '#161E2E', borderRadius: 12,
  border: '1px solid rgba(255,255,255,0.06)',
  padding: 20,
}

const labelStyle = {
  display: 'block', fontSize: 14, fontWeight: 600, color: '#E5E7EB', marginBottom: 2,
}

const descStyle = {
  fontSize: 13, color: '#9CA3AF', margin: 0,
}

const inputStyle = {
  width: '100%', padding: '10px 14px', borderRadius: 8,
  border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)',
  color: '#E5E7EB', fontSize: 14, outline: 'none', boxSizing: 'border-box',
  fontFamily: 'monospace',
}
