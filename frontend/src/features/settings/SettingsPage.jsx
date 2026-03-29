import { useState } from 'react'
import { t } from '../../shared/i18n/translations'
import { getMode, setMode, getApiUrl, setApiUrl as persistApiUrl, checkBackendHealth } from '../../services/api'

export default function SettingsPage({ lang = 'en', setLang, onResetTour }) {
  const [currentMode, setCurrentMode] = useState(() => getMode())
  const [apiUrl, setApiUrl] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('nexusforge_api_url') || ''
    }
    return ''
  })
  const [darkMode] = useState(true)
  const [tourResetDone, setTourResetDone] = useState(false)
  const [backendStatus, setBackendStatus] = useState(null)
  const [testing, setTesting] = useState(false)

  const handleModeChange = (mode) => {
    setCurrentMode(mode)
    setMode(mode)
    // Force re-render of components that read mode
    window.dispatchEvent(new Event('nexusforge-mode-change'))
  }

  const handleApiUrlChange = (value) => {
    setApiUrl(value)
    persistApiUrl(value)
    setBackendStatus(null) // reset status when URL changes
  }

  const testConnection = async () => {
    setTesting(true)
    const health = await checkBackendHealth()
    setBackendStatus(health)
    setTesting(false)
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out', maxWidth: 640 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
        {t('settings', lang)}
      </h1>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 32 }}>
        {t('settingsSubtitle', lang)}
      </p>

      {/* Settings cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Mode Toggle — Demo / Real */}
        <div style={{
          ...cardStyle,
          border: '1px solid rgba(37,99,235,0.3)',
          background: 'rgba(37,99,235,0.02)',
        }}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ ...labelStyle, fontSize: 16 }}>
              {lang === 'es' ? 'Modo de operacion' : 'Operating Mode'}
            </label>
            <p style={descStyle}>
              {lang === 'es'
                ? 'Controla si NexusForge usa datos de ejemplo o se conecta al backend real.'
                : 'Controls whether NexusForge uses built-in demo data or connects to the real backend.'}
            </p>
          </div>

          {/* Toggle buttons */}
          <div style={{ display: 'flex', gap: 0, marginBottom: 16 }}>
            {[
              { key: 'demo', label: 'Demo' },
              { key: 'real', label: 'Real' },
            ].map((option, idx) => (
              <button
                key={option.key}
                onClick={() => handleModeChange(option.key)}
                aria-label={`Mode: ${option.label}`}
                style={{
                  padding: '10px 28px',
                  border: '1px solid',
                  borderColor: currentMode === option.key
                    ? (option.key === 'demo' ? '#F59E0B' : '#10B981')
                    : '#E5E7EB',
                  borderRadius: idx === 0 ? '8px 0 0 8px' : '0 8px 8px 0',
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                  background: currentMode === option.key
                    ? (option.key === 'demo' ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)')
                    : '#FFFFFF',
                  color: currentMode === option.key
                    ? (option.key === 'demo' ? '#D97706' : '#059669')
                    : '#9CA3AF',
                }}
              >
                {option.label}
              </button>
            ))}
          </div>

          {/* Mode description */}
          <div style={{
            padding: '12px 16px', borderRadius: 8, fontSize: 13, lineHeight: 1.6,
            background: currentMode === 'demo' ? 'rgba(245,158,11,0.06)' : 'rgba(16,185,129,0.06)',
            border: `1px solid ${currentMode === 'demo' ? 'rgba(245,158,11,0.2)' : 'rgba(16,185,129,0.2)'}`,
            color: currentMode === 'demo' ? '#92400E' : '#065F46',
          }}>
            {currentMode === 'demo'
              ? (lang === 'es'
                  ? 'Demo: Usa datos de ejemplo integrados. No requiere backend.'
                  : 'Demo: Uses built-in demo data. No backend required.')
              : (lang === 'es'
                  ? 'Real: Se conecta al backend API. Requiere servidor activo.'
                  : 'Real: Connects to backend API. Requires running server.')}
          </div>

          {/* API URL — only visible in Real mode */}
          {currentMode === 'real' && (
            <div style={{ marginTop: 16 }}>
              <label style={{ ...labelStyle, fontSize: 13 }}>
                {lang === 'es' ? 'URL del API (solo modo Real)' : 'API URL (Real mode only)'}
              </label>
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => handleApiUrlChange(e.target.value)}
                placeholder={lang === 'es' ? 'http://localhost:8000/api' : 'http://localhost:8000/api'}
                aria-label="API URL"
                style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = 'rgba(16,185,129,0.4)'}
                onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
              />
              <p style={{ fontSize: 12, color: '#9CA3AF', marginTop: 8, lineHeight: 1.5 }}>
                {lang === 'es'
                  ? 'Local: http://localhost:8000/api | Produccion: URL del backend desplegado'
                  : 'Local: http://localhost:8000/api | Production: deployed backend URL'}
              </p>
            </div>
          )}
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
              background: darkMode ? '#6366F1' : '#D1D5DB',
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
                  background: lang === option.key ? 'rgba(99,102,241,0.2)' : '#F3F4F6',
                  color: lang === option.key ? '#818CF8' : '#9CA3AF',
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {/* Diagnostics */}
        <div style={{
          ...cardStyle,
          border: '1px solid rgba(99,102,241,0.3)',
          background: 'rgba(99,102,241,0.02)',
        }}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ ...labelStyle, fontSize: 16 }}>
              {lang === 'es' ? 'Diagnosticos' : 'Diagnostics'}
            </label>
            <p style={descStyle}>
              {lang === 'es'
                ? 'Estado actual de la conexion y configuracion.'
                : 'Current connection status and configuration.'}
            </p>
          </div>

          {/* Status rows */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
            {/* Current mode */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
              <span style={{ color: '#6B7280' }}>
                {lang === 'es' ? 'Modo actual' : 'Current mode'}
              </span>
              <span style={{
                padding: '2px 10px', borderRadius: 6, fontWeight: 600,
                background: currentMode === 'demo' ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)',
                color: currentMode === 'demo' ? '#D97706' : '#059669',
              }}>
                {currentMode === 'demo' ? 'Demo' : 'Real'}
              </span>
            </div>

            {/* API URL */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
              <span style={{ color: '#6B7280' }}>
                {lang === 'es' ? 'URL del API' : 'API URL'}
              </span>
              <span style={{
                fontFamily: 'monospace', fontSize: 12,
                color: apiUrl ? '#374151' : '#9CA3AF',
                maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {apiUrl || (lang === 'es' ? 'No configurada' : 'Not configured')}
              </span>
            </div>

            {/* Backend status */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
              <span style={{ color: '#6B7280' }}>
                {lang === 'es' ? 'Estado del backend' : 'Backend status'}
              </span>
              {backendStatus ? (
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '2px 10px', borderRadius: 6, fontWeight: 600, fontSize: 12,
                  background: backendStatus.status === 'connected' ? 'rgba(16,185,129,0.1)'
                    : backendStatus.status === 'no_url' ? 'rgba(156,163,175,0.15)'
                    : 'rgba(220,38,38,0.1)',
                  color: backendStatus.status === 'connected' ? '#059669'
                    : backendStatus.status === 'no_url' ? '#6B7280'
                    : '#DC2626',
                }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: backendStatus.status === 'connected' ? '#10B981'
                      : backendStatus.status === 'no_url' ? '#9CA3AF'
                      : '#DC2626',
                  }} />
                  {backendStatus.status === 'connected'
                    ? (lang === 'es' ? 'Conectado' : 'Connected')
                    : backendStatus.status === 'no_url'
                      ? (lang === 'es' ? 'Sin URL' : 'No URL')
                      : (lang === 'es' ? 'No disponible' : 'Unreachable')}
                </span>
              ) : (
                <span style={{ color: '#9CA3AF', fontSize: 12 }}>
                  {lang === 'es' ? 'No verificado' : 'Not tested'}
                </span>
              )}
            </div>

            {/* Error message */}
            {backendStatus && backendStatus.status !== 'connected' && (
              <div style={{
                padding: '8px 12px', borderRadius: 6, fontSize: 12,
                background: backendStatus.status === 'no_url' ? 'rgba(156,163,175,0.08)' : 'rgba(220,38,38,0.06)',
                border: `1px solid ${backendStatus.status === 'no_url' ? 'rgba(156,163,175,0.2)' : 'rgba(220,38,38,0.2)'}`,
                color: backendStatus.status === 'no_url' ? '#6B7280' : '#991B1B',
                lineHeight: 1.5,
              }}>
                {backendStatus.message}
              </div>
            )}
          </div>

          {/* Test Connection button */}
          <button
            onClick={testConnection}
            disabled={testing}
            style={{
              padding: '10px 24px', borderRadius: 8,
              border: '1px solid rgba(99,102,241,0.3)',
              background: testing ? '#F3F4F6' : 'transparent',
              color: testing ? '#9CA3AF' : '#818CF8',
              fontSize: 14, fontWeight: 500,
              cursor: testing ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {testing
              ? (lang === 'es' ? 'Probando...' : 'Testing...')
              : (lang === 'es' ? 'Probar conexion' : 'Test Connection')}
          </button>
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
  background: '#FFFFFF', borderRadius: 12,
  border: '1px solid #E5E7EB',
  padding: 20,
}

const labelStyle = {
  display: 'block', fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 2,
}

const descStyle = {
  fontSize: 13, color: '#9CA3AF', margin: 0,
}

const inputStyle = {
  width: '100%', padding: '10px 14px', borderRadius: 8,
  border: '1px solid #E5E7EB', background: '#F3F4F6',
  color: '#111827', fontSize: 14, outline: 'none', boxSizing: 'border-box',
  fontFamily: 'monospace',
}
