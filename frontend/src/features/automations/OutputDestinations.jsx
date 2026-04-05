import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

const DESTINATIONS = [
  { key: 'email', icon: '✉️', label: { es: 'Email', en: 'Email' }, service: 'email' },
  { key: 'slack', icon: '💬', label: { es: 'Slack', en: 'Slack' }, service: 'slack' },
  { key: 'notion', icon: '📝', label: { es: 'Notion', en: 'Notion' }, service: 'notion' },
  { key: 'drive', icon: '📁', label: { es: 'Google Drive', en: 'Google Drive' }, service: 'drive' },
  { key: 'webhook', icon: '🔗', label: { es: 'Webhook', en: 'Webhook' }, service: null },
]

export default function OutputDestinations({ automationId, lang = 'en' }) {
  const [config, setConfig] = useState({})
  const [integrations, setIntegrations] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [webhookUrl, setWebhookUrl] = useState('')

  useEffect(() => {
    if (!automationId) return
    setLoading(true)
    Promise.all([
      fetchAPI(`/automations/${automationId}/output-config`),
      fetchAPI('/integrations/services'),
    ]).then(([configRes, intRes]) => {
      if (!configRes.error && configRes.data?.output_config) {
        setConfig(configRes.data.output_config)
        setWebhookUrl(configRes.data.output_config.webhook_url || '')
      }
      if (!intRes.error) {
        const map = {}
        const items = intRes.data?.services || intRes.data || []
        if (Array.isArray(items)) {
          items.forEach(s => { map[s.service] = s })
        }
        setIntegrations(map)
      }
      setLoading(false)
    })
  }, [automationId])

  const toggle = async (key) => {
    const next = { ...config, [key]: !config[key] }
    setConfig(next)
    setSaving(true)
    await fetchAPI(`/automations/${automationId}/output-config`, {
      method: 'PUT',
      body: JSON.stringify({ output_config: { ...next, webhook_url: webhookUrl } }),
    })
    setSaving(false)
  }

  const saveWebhookUrl = async () => {
    setSaving(true)
    const next = { ...config, webhook_url: webhookUrl }
    setConfig(next)
    await fetchAPI(`/automations/${automationId}/output-config`, {
      method: 'PUT',
      body: JSON.stringify({ output_config: next }),
    })
    setSaving(false)
  }

  if (loading) {
    return (
      <div style={{ padding: 24, color: '#9CA3AF', fontSize: 13 }}>
        {lang === 'es' ? 'Cargando destinos...' : 'Loading destinations...'}
      </div>
    )
  }

  const activeCount = DESTINATIONS.filter(d => config[d.key]).length

  return (
    <div style={{ animation: 'fadeIn 0.2s ease-out' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: '#111827', margin: '0 0 4px' }}>
            {lang === 'es' ? 'Destinos de Salida' : 'Output Destinations'}
          </h3>
          <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0 }}>
            {lang === 'es'
              ? 'Selecciona a donde enviar los resultados de cada ejecucion'
              : 'Choose where to send results after each execution'}
          </p>
        </div>
        {saving && (
          <span style={{ fontSize: 11, color: '#6366F1', fontWeight: 500 }}>
            {lang === 'es' ? 'Guardando...' : 'Saving...'}
          </span>
        )}
        {!saving && activeCount > 0 && (
          <span style={{
            fontSize: 11, padding: '3px 8px', borderRadius: 6,
            background: '#D1FAE5', color: '#059669', fontWeight: 600,
          }}>
            {activeCount} {lang === 'es' ? 'activo' : 'active'}{activeCount > 1 ? 's' : ''}
          </span>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
        {DESTINATIONS.map(dest => {
          const enabled = !!config[dest.key]
          const integrated = dest.service ? integrations[dest.service] : true
          const configured = integrated?.is_active || integrated?.test_status === 'ok' || dest.key === 'webhook'
          const needsSetup = dest.service && !integrated

          return (
            <div
              key={dest.key}
              onClick={() => !needsSetup && toggle(dest.key)}
              style={{
                padding: '12px 14px', borderRadius: 10,
                border: `1.5px solid ${enabled ? '#10B981' : needsSetup ? '#E5E7EB' : '#D1D5DB'}`,
                background: enabled ? 'rgba(16,185,129,0.04)' : needsSetup ? '#FAFAFA' : '#fff',
                cursor: needsSetup ? 'not-allowed' : 'pointer',
                opacity: needsSetup ? 0.6 : 1,
                transition: 'all 0.15s',
                display: 'flex', alignItems: 'center', gap: 10,
              }}
            >
              <span style={{ fontSize: 20, flexShrink: 0 }}>{dest.icon}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: 13, fontWeight: 600, color: '#111827', margin: 0 }}>
                  {dest.label[lang] || dest.label.en}
                </p>
                <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>
                  {needsSetup
                    ? (lang === 'es' ? 'No configurado' : 'Not configured')
                    : enabled
                      ? (lang === 'es' ? 'Activado' : 'Enabled')
                      : (lang === 'es' ? 'Desactivado' : 'Disabled')}
                </p>
              </div>
              <div style={{
                width: 18, height: 18, borderRadius: 4, flexShrink: 0,
                border: `2px solid ${enabled ? '#10B981' : '#D1D5DB'}`,
                background: enabled ? '#10B981' : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.15s',
              }}>
                {enabled && (
                  <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Webhook URL input */}
      {config.webhook && (
        <div style={{ marginTop: 12 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 4 }}>
            Webhook URL
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="url"
              value={webhookUrl}
              onChange={e => setWebhookUrl(e.target.value)}
              placeholder="https://..."
              style={{
                flex: 1, padding: '8px 12px', borderRadius: 8,
                border: '1px solid #D1D5DB', fontSize: 13,
              }}
            />
            <button
              onClick={saveWebhookUrl}
              style={{
                padding: '8px 14px', borderRadius: 8, border: 'none',
                background: '#6366F1', color: '#fff', fontSize: 12,
                fontWeight: 600, cursor: 'pointer',
              }}
            >
              {lang === 'es' ? 'Guardar' : 'Save'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
