import { useState } from 'react'
import { t } from '../../shared/i18n/translations'
import { getApiUrl, setApiUrl as persistApiUrl, checkBackendHealth } from '../../services/api'

export default function SettingsPage({ lang = 'en', setLang, onResetTour, theme = 'light', setTheme }) {
  const [apiUrl, setApiUrl] = useState(() => getApiUrl())
  const isDark = theme === 'dark'
  const [tourResetDone, setTourResetDone] = useState(false)
  const [backendStatus, setBackendStatus] = useState(null)
  const [testing, setTesting] = useState(false)

  const handleApiUrlChange = (value) => {
    setApiUrl(value)
    persistApiUrl(value)
    setBackendStatus(null)
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

        {/* API Connection */}
        <div style={{
          ...cardStyle,
          border: '1px solid rgba(37,99,235,0.3)',
          background: 'rgba(37,99,235,0.02)',
        }}>

          {/* API URL */}
          <div>
              <label style={{ ...labelStyle, fontSize: 13 }}>
                {lang === 'es' ? 'URL del Backend API' : 'Backend API URL'}
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
        </div>

        {/* Theme */}
        <div style={isDark ? cardStyleDark : cardStyle}>
          <div style={{ marginBottom: 12 }}>
            <label style={isDark ? labelStyleDark : labelStyle}>{t('theme', lang)}</label>
            <p style={descStyle}>{t('themeDesc', lang)}</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => setTheme && setTheme('light')}
              style={{
                padding: '8px 20px', borderRadius: 8,
                background: !isDark ? '#2563EB' : 'transparent',
                color: !isDark ? '#fff' : '#6B7280',
                border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'}`,
                cursor: 'pointer', fontSize: 14, fontWeight: 500,
                transition: 'all 0.15s',
              }}
            >
              {lang === 'es' ? 'Claro' : 'Light'}
            </button>
            <button
              onClick={() => setTheme && setTheme('dark')}
              style={{
                padding: '8px 20px', borderRadius: 8,
                background: isDark ? '#6366F1' : 'transparent',
                color: isDark ? '#fff' : '#6B7280',
                border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'}`,
                cursor: 'pointer', fontSize: 14, fontWeight: 500,
                transition: 'all 0.15s',
              }}
            >
              {lang === 'es' ? 'Oscuro' : 'Dark'}
            </button>
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
              { key: 'es', label: 'Español' },
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
              {lang === 'es' ? 'Diagnósticos' : 'Diagnostics'}
            </label>
            <p style={descStyle}>
              {lang === 'es'
                ? 'Estado actual de la conexión y configuración.'
                : 'Current connection status and configuration.'}
            </p>
          </div>

          {/* Status rows */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
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

            {/* Connection status */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
              <span style={{ color: '#6B7280' }}>
                {lang === 'es' ? 'Estado' : 'Status'}
              </span>
              <span style={{
                padding: '2px 10px', borderRadius: 6, fontWeight: 600,
                background: apiUrl ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
                color: apiUrl ? '#059669' : '#D97706',
              }}>
                {apiUrl ? (lang === 'es' ? 'Conectado' : 'Connected') : (lang === 'es' ? 'Sin configurar' : 'Not configured')}
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
              : (lang === 'es' ? 'Probar conexión' : 'Test Connection')}
          </button>
        </div>

        {/* Account */}
        <AccountSection lang={lang} />

        {/* Billing / Plan */}
        <BillingSection lang={lang} />

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
            <div style={{ textAlign: 'right' }}>
              <span style={{
                fontSize: 14, fontWeight: 600, color: '#6366F1',
                fontFamily: 'monospace',
              }}>v2.5.0</span>
              <p style={{ fontSize: 10, color: '#D1D5DB', margin: '2px 0 0' }}>
                103 modules &middot; 24 agents &middot; 37 components
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}

const PLANS = [
  { id: 'free', name: 'Free', price: '$0', limit: '5 runs/day', color: '#6B7280' },
  { id: 'pro', name: 'Pro', price: '$29/mo', limit: '100 runs/day', color: '#6366F1' },
  { id: 'team', name: 'Team', price: '$99/mo', limit: '500 runs/day', color: '#8B5CF6' },
  { id: 'enterprise', name: 'Enterprise', price: 'Custom', limit: 'Unlimited', color: '#059669' },
]

function BillingSection({ lang }) {
  const user = (() => { try { return JSON.parse(localStorage.getItem('nf_user') || '{}') } catch { return {} } })()
  if (user.isGuest) return null
  const currentPlan = user.plan || 'free'

  return (
    <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 20 }}>
      <label style={{ display: 'block', fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 2 }}>
        {lang === 'es' ? 'Plan y Facturacion' : 'Plan & Billing'}
      </label>
      <p style={{ fontSize: 13, color: '#9CA3AF', margin: '0 0 16px' }}>
        {lang === 'es' ? 'Tu plan actual y opciones de upgrade.' : 'Your current plan and upgrade options.'}
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
        {PLANS.map(plan => {
          const isCurrent = plan.id === currentPlan
          return (
            <div key={plan.id} style={{
              padding: 14, borderRadius: 10,
              border: `2px solid ${isCurrent ? plan.color : '#E5E7EB'}`,
              background: isCurrent ? `${plan.color}08` : '#fff',
              textAlign: 'center', position: 'relative',
            }}>
              {isCurrent && (
                <div style={{
                  position: 'absolute', top: -8, left: '50%', transform: 'translateX(-50%)',
                  background: plan.color, color: '#fff', fontSize: 9, fontWeight: 700,
                  padding: '2px 8px', borderRadius: 4, textTransform: 'uppercase',
                }}>
                  {lang === 'es' ? 'Actual' : 'Current'}
                </div>
              )}
              <div style={{ fontSize: 14, fontWeight: 700, color: '#111827', marginBottom: 4, marginTop: isCurrent ? 4 : 0 }}>
                {plan.name}
              </div>
              <div style={{ fontSize: 18, fontWeight: 800, color: plan.color, marginBottom: 4 }}>
                {plan.price}
              </div>
              <div style={{ fontSize: 11, color: '#9CA3AF' }}>{plan.limit}</div>
              {!isCurrent && plan.id !== 'free' && (
                <button style={{
                  marginTop: 8, padding: '5px 12px', borderRadius: 6, border: `1px solid ${plan.color}`,
                  background: 'transparent', color: plan.color, fontSize: 11, fontWeight: 600,
                  cursor: 'pointer',
                }}>
                  {lang === 'es' ? 'Upgrade' : 'Upgrade'}
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function AccountSection({ lang }) {
  const user = (() => { try { return JSON.parse(localStorage.getItem('nf_user') || '{}') } catch { return {} } })()
  const [name, setName] = useState(user.name || '')
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  const handleSave = async () => {
    setSaving(true)
    setMsg('')
    try {
      // Update name
      if (name !== user.name) {
        const updated = { ...user, name }
        localStorage.setItem('nf_user', JSON.stringify(updated))
      }
      // Change password
      if (currentPw && newPw && newPw.length >= 6) {
        const { fetchAPI } = await import('../../services/api')
        const res = await fetchAPI('/auth/change-password', {
          method: 'POST',
          body: JSON.stringify({ current_password: currentPw, new_password: newPw }),
        })
        if (res.error) {
          setMsg(res.error)
          setSaving(false)
          return
        }
      }
      setMsg(lang === 'es' ? 'Guardado' : 'Saved')
      setCurrentPw('')
      setNewPw('')
    } catch (e) {
      setMsg(e.message)
    }
    setSaving(false)
  }

  if (user.isGuest) return null

  const fieldStyle = {
    width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid #E5E7EB',
    fontSize: 14, outline: 'none', boxSizing: 'border-box', marginBottom: 12,
  }

  return (
    <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 20 }}>
      <label style={{ display: 'block', fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 2 }}>
        {lang === 'es' ? 'Cuenta' : 'Account'}
      </label>
      <p style={{ fontSize: 13, color: '#9CA3AF', margin: '0 0 16px' }}>
        {user.email} &middot; {user.plan || 'free'}
      </p>

      <label style={{ fontSize: 12, fontWeight: 600, color: '#374151' }}>
        {lang === 'es' ? 'Nombre' : 'Name'}
      </label>
      <input value={name} onChange={e => setName(e.target.value)} style={fieldStyle} />

      <label style={{ fontSize: 12, fontWeight: 600, color: '#374151' }}>
        {lang === 'es' ? 'Contraseña actual' : 'Current password'}
      </label>
      <input type="password" value={currentPw} onChange={e => setCurrentPw(e.target.value)}
        placeholder="••••••" style={fieldStyle} />

      <label style={{ fontSize: 12, fontWeight: 600, color: '#374151' }}>
        {lang === 'es' ? 'Nueva contraseña' : 'New password'}
      </label>
      <input type="password" value={newPw} onChange={e => setNewPw(e.target.value)}
        placeholder={lang === 'es' ? 'Min 6 caracteres' : 'Min 6 characters'} style={fieldStyle} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={handleSave} disabled={saving} style={{
          padding: '9px 20px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 600,
          background: saving ? '#A5B4FC' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
          color: '#fff', cursor: saving ? 'default' : 'pointer',
        }}>{saving ? '...' : (lang === 'es' ? 'Guardar' : 'Save')}</button>
        {msg && <span style={{ fontSize: 12, color: msg === 'Saved' || msg === 'Guardado' ? '#10B981' : '#EF4444' }}>{msg}</span>}
      </div>

      {/* Data export */}
      <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #F3F4F6' }}>
        <button onClick={async () => {
          const { fetchAPI } = await import('../../services/api')
          const res = await fetchAPI('/auth/export-data')
          if (res.data) {
            const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `nexusforge-data-${new Date().toISOString().slice(0, 10)}.json`
            a.click()
            URL.revokeObjectURL(url)
          }
        }} style={{
          padding: '8px 16px', borderRadius: 8, border: '1px solid #E5E7EB',
          background: '#fff', fontSize: 12, color: '#6B7280', cursor: 'pointer', fontWeight: 600,
        }}>
          {lang === 'es' ? 'Exportar mis datos (JSON)' : 'Export my data (JSON)'}
        </button>
      </div>
    </div>
  )
}

const cardStyle = {
  background: '#FFFFFF', borderRadius: 12,
  border: '1px solid #E5E7EB',
  padding: 20,
}

const cardStyleDark = {
  background: '#1E1F33', borderRadius: 12,
  border: '1px solid rgba(255,255,255,0.08)',
  padding: 20,
}

const labelStyle = {
  display: 'block', fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 2,
}

const labelStyleDark = {
  display: 'block', fontSize: 14, fontWeight: 600, color: '#E5E7EB', marginBottom: 2,
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
