import { useState } from 'react'
import { api } from '../../api/client'
import { t } from '../../shared/i18n/translations'

export default function SettingsPage({ lang = 'en', setLang, onResetTour }) {
  const [apiUrl, setApiUrl] = useState(
    () => (typeof window !== 'undefined' && import.meta.env.VITE_API_URL) || 'http://localhost:8000/api'
  )
  const [darkMode] = useState(true)
  const [healthResult, setHealthResult] = useState(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const [tourResetDone, setTourResetDone] = useState(false)

  const checkHealth = async () => {
    setHealthLoading(true)
    setHealthResult(null)
    try {
      const data = await api.get('/health')
      setHealthResult({ ok: true, data })
    } catch (err) {
      setHealthResult({ ok: false, error: err.message || 'Connection failed' })
    } finally {
      setHealthLoading(false)
    }
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out', maxWidth: 640 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 4 }}>
        {t('settings', lang)}
      </h1>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 32 }}>
        {t('settingsSubtitle', lang)}
      </p>

      {/* Settings cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* API URL */}
        <div style={cardStyle}>
          <div style={{ marginBottom: 12 }}>
            <label style={labelStyle}>{t('apiBaseUrl', lang)}</label>
            <p style={descStyle}>{t('apiBaseUrlDesc', lang)}</p>
          </div>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            aria-label={t('apiBaseUrl', lang)}
            style={inputStyle}
            onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
            onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
          />
        </div>

        {/* Theme */}
        <div style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <label style={labelStyle}>{t('theme', lang)}</label>
              <p style={descStyle}>{t('themeDesc', lang)}</p>
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
            <label style={labelStyle}>{t('language', lang)}</label>
            <p style={descStyle}>{t('languageDesc', lang)}</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {[
              { key: 'es', label: 'Espanol' },
              { key: 'en', label: 'English' },
            ].map((option) => (
              <button
                key={option.key}
                onClick={() => setLang && setLang(option.key)}
                aria-label={`${t('language', lang)}: ${option.label}`}
                style={{
                  padding: '8px 20px', borderRadius: 8, border: 'none', fontSize: 14,
                  fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s',
                  background: lang === option.key ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.04)',
                  color: lang === option.key ? '#818CF8' : '#9CA3AF',
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {/* Health Check */}
        <div style={cardStyle}>
          <div style={{ marginBottom: 12 }}>
            <label style={labelStyle}>{t('apiStatus', lang)}</label>
            <p style={descStyle}>{t('apiStatusDesc', lang)}</p>
          </div>
          <button
            onClick={checkHealth}
            disabled={healthLoading}
            aria-label={t('healthCheck', lang)}
            style={{
              padding: '10px 24px', borderRadius: 8, border: 'none',
              background: healthLoading ? 'rgba(99,102,241,0.3)' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              color: '#fff', fontSize: 14, fontWeight: 600,
              cursor: healthLoading ? 'not-allowed' : 'pointer',
              marginBottom: healthResult ? 12 : 0,
            }}
          >
            {healthLoading ? t('verifying', lang) : t('verifyConnection', lang)}
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
                ? `${t('apiOperative', lang)}: ${JSON.stringify(healthResult.data)}`
                : `${t('error', lang)}: ${healthResult.error}`
              }
            </div>
          )}
        </div>

        {/* Reset Tour */}
        <div style={cardStyle}>
          <div style={{ marginBottom: 12 }}>
            <label style={labelStyle}>{t('resetTour', lang)}</label>
            <p style={descStyle}>{t('resetTourDesc', lang)}</p>
          </div>
          <button
            onClick={() => { onResetTour && onResetTour(); setTourResetDone(true) }}
            aria-label={t('resetTourBtn', lang)}
            style={{
              padding: '10px 24px', borderRadius: 8,
              border: '1px solid rgba(99,102,241,0.3)',
              background: 'transparent',
              color: '#818CF8', fontSize: 14, fontWeight: 500,
              cursor: 'pointer', transition: 'all 0.15s',
              marginBottom: tourResetDone ? 12 : 0,
            }}
          >
            {t('resetTourBtn', lang)}
          </button>
          {tourResetDone && (
            <div style={{
              padding: '10px 16px', borderRadius: 8,
              background: 'rgba(16,185,129,0.08)',
              border: '1px solid rgba(16,185,129,0.2)',
              color: '#10B981', fontSize: 13,
            }}>
              {t('tourReset', lang)}
            </div>
          )}
        </div>

        {/* Version */}
        <div style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <label style={labelStyle}>{t('versionLabel', lang)}</label>
              <p style={descStyle}>{t('versionDesc', lang)}</p>
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
