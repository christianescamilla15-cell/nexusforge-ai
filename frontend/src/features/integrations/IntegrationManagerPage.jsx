import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

// ── Icons ────────────────────────────────────────────────────────────────────

const ICONS = {
  mail: 'M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75',
  edit: 'M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10',
  'message-circle': 'M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z',
  link: 'M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244',
  phone: 'M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z',
  folder: 'M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z',
  inbox: 'M2.25 13.5h3.86a2.25 2.25 0 012.012 1.244l.256.512a2.25 2.25 0 002.013 1.244h3.218a2.25 2.25 0 002.013-1.244l.256-.512a2.25 2.25 0 012.013-1.244h3.859m-19.5.338V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18v-4.162c0-.224-.034-.447-.1-.661L19.24 5.338a2.25 2.25 0 00-2.15-1.588H6.911a2.25 2.25 0 00-2.15 1.588L2.35 13.177a2.25 2.25 0 00-.1.661z',
  calendar: 'M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5',
}

function Icon({ name, size = 18, color = 'currentColor' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d={ICONS[name] || ICONS.link} />
    </svg>
  )
}

// ── Help tooltips ─────────────────────────────────────────────────────────────

const HELP = {
  groq: {
    es: 'Motor LLM rápido y económico. Obtén tu key en console.groq.com → API Keys → Create.',
    en: 'Fast, affordable LLM engine. Get your key at console.groq.com → API Keys → Create.',
  },
  claude: {
    es: 'IA de alta calidad de Anthropic. Key en console.anthropic.com → API Keys.',
    en: 'High-quality AI by Anthropic. Key at console.anthropic.com → API Keys.',
  },
  'openai-gpt4o': {
    es: 'Modelo potente de OpenAI. Key en platform.openai.com → API Keys → Create.',
    en: 'Powerful OpenAI model. Key at platform.openai.com → API Keys → Create.',
  },
  openai: {
    es: 'Versión económica de GPT-4o. Misma key de OpenAI: platform.openai.com → API Keys.',
    en: 'Budget GPT-4o version. Same OpenAI key: platform.openai.com → API Keys.',
  },
  email: {
    es: 'Envía resultados por correo vía Resend. Key en resend.com → API Keys. Gratis hasta 100 emails/día.',
    en: 'Send results via email through Resend. Key at resend.com → API Keys. Free up to 100 emails/day.',
  },
  notion: {
    es: 'Guarda resultados en Notion. Crea integración en notion.so/my-integrations → New → copia el token. Comparte la DB con la integración.',
    en: 'Save results to Notion. Create integration at notion.so/my-integrations → New → copy token. Share the DB with the integration.',
  },
  slack: {
    es: 'Recibe alertas en Slack. Crea app en api.slack.com/apps → Incoming Webhooks → Add → copia la URL.',
    en: 'Receive alerts in Slack. Create app at api.slack.com/apps → Incoming Webhooks → Add → copy URL.',
  },
  webhook: {
    es: 'Envía resultados a cualquier URL como POST JSON. Opcionalmente firma con HMAC para seguridad.',
    en: 'Send results to any URL as POST JSON. Optionally sign with HMAC for security.',
  },
  whatsapp: {
    es: 'Envía por WhatsApp vía Twilio. Registra en twilio.com → Console → Account SID y Auth Token.',
    en: 'Send via WhatsApp through Twilio. Register at twilio.com → Console → Account SID and Auth Token.',
  },
  drive: {
    es: 'Lee archivos de Google Drive. Crea Service Account en console.cloud.google.com → APIs → Credentials → descarga JSON.',
    en: 'Read files from Google Drive. Create Service Account at console.cloud.google.com → APIs → Credentials → download JSON.',
  },
  gmail: {
    es: 'Lee correos de Gmail. Requiere OAuth 2.0: console.cloud.google.com → APIs → OAuth → descarga JSON.',
    en: 'Read emails from Gmail. Requires OAuth 2.0: console.cloud.google.com → APIs → OAuth → download JSON.',
  },
  calendar: {
    es: 'Accede a Google Calendar. Service Account en console.cloud.google.com → comparte calendario con la cuenta.',
    en: 'Access Google Calendar. Service Account at console.cloud.google.com → share calendar with the account.',
  },
}

function HelpBadge({ id, lang = 'en' }) {
  const [show, setShow] = useState(false)
  const text = HELP[id]?.[lang] || HELP[id]?.en || ''
  if (!text) return null

  return (
    <div style={{ position: 'relative', display: 'inline-flex' }}>
      <div
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        style={{
          width: 18, height: 18, borderRadius: '50%', background: '#F3F4F6',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'help', flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 10, fontWeight: 700, color: '#9CA3AF' }}>?</span>
      </div>
      {show && (
        <div style={{
          position: 'absolute', bottom: '130%', left: '50%', transform: 'translateX(-50%)',
          width: 260, zIndex: 100, padding: '10px 12px', borderRadius: 10,
          background: '#1F2937', color: '#F9FAFB', fontSize: 12, lineHeight: 1.5,
          boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
          textAlign: 'left',
        }}>
          {text}
          <div style={{
            position: 'absolute', bottom: -6, left: '50%', transform: 'translateX(-50%)',
            width: 0, height: 0, borderLeft: '6px solid transparent',
            borderRight: '6px solid transparent', borderTop: '6px solid #1F2937',
          }} />
        </div>
      )}
    </div>
  )
}

// ── Speed badge ───────────────────────────────────────────────────────────────

function SpeedBadge({ speed }) {
  const map = {
    fast: { label: 'Fast', bg: '#F0FDF4', color: '#16A34A', border: '#BBF7D0' },
    medium: { label: 'Medium', bg: '#FFF7ED', color: '#C2410C', border: '#FED7AA' },
    slow: { label: 'Slow', bg: '#FEF2F2', color: '#DC2626', border: '#FECACA' },
  }
  const s = map[speed] || map.medium
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 600,
      background: s.bg, color: s.color, border: `1px solid ${s.border}`,
    }}>{s.label}</span>
  )
}

// ── LLM Provider card ─────────────────────────────────────────────────────────

function ProviderCard({ provider, savedKey, onSaved, lang = 'en' }) {
  const [key, setKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)
  const configured = !!savedKey

  const handleSave = async () => {
    if (!key.trim()) return
    setSaving(true)
    const res = await fetchAPI('/integrations/providers/keys', {
      method: 'POST',
      body: JSON.stringify({ provider: provider.id, api_key: key.trim() }),
    })
    setSaving(false)
    if (res.error) {
      setMsg({ type: 'error', text: res.error })
    } else {
      setMsg({ type: 'ok', text: lang === 'es' ? 'Clave guardada' : 'Key saved' })
      setKey('')
      onSaved(provider.id)
      setTimeout(() => setMsg(null), 2500)
    }
  }

  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: `1px solid ${configured ? '#BBF7D0' : '#E5E7EB'}`,
      padding: 20, display: 'flex', flexDirection: 'column', gap: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 15, fontWeight: 700, color: '#111827' }}>{provider.name}</span>
            <HelpBadge id={provider.id} lang={lang} />
            {configured && (
              <span style={{ fontSize: 18, lineHeight: 1 }} title="Configured">✅</span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <SpeedBadge speed={provider.speed} />
            <span style={{ fontSize: 11, color: '#9CA3AF' }}>
              ${provider.pricing.input}/M in · ${provider.pricing.output}/M out
            </span>
          </div>
        </div>
      </div>

      {configured && (
        <div style={{
          padding: '6px 10px', borderRadius: 6, background: '#F0FDF4',
          border: '1px solid #BBF7D0', fontSize: 12, color: '#16A34A',
          fontFamily: 'monospace',
        }}>
          {savedKey.preview}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          type="password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder={provider.key_placeholder}
          onKeyDown={(e) => e.key === 'Enter' && handleSave()}
          style={{
            flex: 1, padding: '8px 12px', borderRadius: 7, fontSize: 13,
            border: '1px solid #E5E7EB', outline: 'none', fontFamily: 'monospace',
          }}
        />
        <button
          onClick={handleSave}
          disabled={saving || !key.trim()}
          style={{
            padding: '8px 16px', borderRadius: 7, border: 'none',
            background: saving || !key.trim() ? '#E5E7EB' : '#6366F1',
            color: saving || !key.trim() ? '#9CA3AF' : '#fff',
            fontSize: 13, fontWeight: 600, cursor: saving || !key.trim() ? 'not-allowed' : 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          {saving ? (lang === 'es' ? 'Guardando…' : 'Saving…') : configured ? (lang === 'es' ? 'Actualizar' : 'Update') : (lang === 'es' ? 'Guardar' : 'Save')}
        </button>
      </div>

      {msg && (
        <div style={{
          fontSize: 12, padding: '6px 10px', borderRadius: 6,
          background: msg.type === 'ok' ? '#F0FDF4' : '#FEF2F2',
          color: msg.type === 'ok' ? '#16A34A' : '#DC2626',
          border: `1px solid ${msg.type === 'ok' ? '#BBF7D0' : '#FECACA'}`,
        }}>{msg.text}</div>
      )}

      <div style={{ fontSize: 11, color: '#9CA3AF' }}>
        {lang === 'es' ? 'Modelos' : 'Models'}: {provider.models.join(', ')}
      </div>
    </div>
  )
}

// ── Service integration card ──────────────────────────────────────────────────

function ServiceCard({ service, onSaved }) {
  const [expanded, setExpanded] = useState(false)
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  const handleSave = async () => {
    setSaving(true)
    const res = await fetchAPI('/integrations/services/configure', {
      method: 'POST',
      body: JSON.stringify({ service: service.id, config: form }),
    })
    setSaving(false)
    if (res.error) {
      setMsg({ type: 'error', text: res.error })
    } else {
      setMsg({ type: 'ok', text: 'Integration saved' })
      onSaved(service.id)
      setTimeout(() => { setMsg(null); setExpanded(false) }, 2000)
    }
  }

  const categoryColor = service.category === 'input'
    ? { bg: '#EFF6FF', color: '#2563EB', border: '#BFDBFE' }
    : { bg: '#F5F3FF', color: '#7C3AED', border: '#DDD6FE' }

  return (
    <div style={{
      background: '#fff', borderRadius: 12,
      border: `1px solid ${service.configured ? '#BBF7D0' : '#E5E7EB'}`,
      overflow: 'hidden', transition: 'box-shadow 0.15s',
    }}>
      {/* Header row */}
      <div
        onClick={() => setExpanded((v) => !v)}
        style={{
          display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px',
          cursor: 'pointer', userSelect: 'none',
        }}
      >
        <div style={{
          width: 36, height: 36, borderRadius: 8, display: 'flex', alignItems: 'center',
          justifyContent: 'center', background: '#F3F4F6', flexShrink: 0,
        }}>
          <Icon name={service.icon} size={18} color="#6B7280" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{service.name}</span>
            <HelpBadge id={service.id} lang={service._lang || 'en'} />
            {service.configured && <span title="Configured">✅</span>}
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 3 }}>
            <span style={{
              fontSize: 10, fontWeight: 600, padding: '1px 7px', borderRadius: 20,
              background: categoryColor.bg, color: categoryColor.color, border: `1px solid ${categoryColor.border}`,
              textTransform: 'uppercase',
            }}>{service.category}</span>
            {service.configured && (
              <span style={{ fontSize: 11, color: '#16A34A' }}>Configured</span>
            )}
          </div>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" strokeWidth="2"
          style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s', flexShrink: 0 }}>
          <path d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Expanded form */}
      {expanded && (
        <div style={{ padding: '0 16px 16px', borderTop: '1px solid #F3F4F6' }}>
          <div style={{ paddingTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {service.fields.map((field) => (
              <div key={field.key}>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 }}>
                  {field.label}
                </label>
                {field.type === 'textarea' ? (
                  <textarea
                    value={form[field.key] || ''}
                    onChange={(e) => setForm((f) => ({ ...f, [field.key]: e.target.value }))}
                    placeholder={field.placeholder || ''}
                    rows={4}
                    style={{
                      width: '100%', padding: '8px 10px', borderRadius: 7, fontSize: 12,
                      border: '1px solid #E5E7EB', outline: 'none', resize: 'vertical',
                      fontFamily: 'monospace', boxSizing: 'border-box',
                    }}
                  />
                ) : (
                  <input
                    type={field.type === 'password' ? 'password' : 'text'}
                    value={form[field.key] || ''}
                    onChange={(e) => setForm((f) => ({ ...f, [field.key]: e.target.value }))}
                    placeholder={field.placeholder || ''}
                    style={{
                      width: '100%', padding: '8px 10px', borderRadius: 7, fontSize: 13,
                      border: '1px solid #E5E7EB', outline: 'none', boxSizing: 'border-box',
                      fontFamily: field.type === 'password' ? 'monospace' : 'inherit',
                    }}
                  />
                )}
              </div>
            ))}
          </div>

          {msg && (
            <div style={{
              marginTop: 10, fontSize: 12, padding: '6px 10px', borderRadius: 6,
              background: msg.type === 'ok' ? '#F0FDF4' : '#FEF2F2',
              color: msg.type === 'ok' ? '#16A34A' : '#DC2626',
              border: `1px solid ${msg.type === 'ok' ? '#BBF7D0' : '#FECACA'}`,
            }}>{msg.text}</div>
          )}

          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                padding: '8px 18px', borderRadius: 7, border: 'none',
                background: saving ? '#A5B4FC' : '#6366F1', color: '#fff',
                fontSize: 13, fontWeight: 600, cursor: saving ? 'not-allowed' : 'pointer',
              }}
            >
              {saving ? 'Saving…' : 'Save Integration'}
            </button>
            <button
              onClick={() => setExpanded(false)}
              style={{
                padding: '8px 14px', borderRadius: 7, border: '1px solid #E5E7EB',
                background: '#fff', color: '#6B7280', fontSize: 13, cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function IntegrationManagerPage({ lang = 'en' }) {
  const [providers, setProviders] = useState([])
  const [savedKeys, setSavedKeys] = useState({}) // { provider_id: { preview } }
  const [services, setServices] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    const [provRes, keysRes, svcRes] = await Promise.all([
      fetchAPI('/integrations/providers'),
      fetchAPI('/integrations/providers/keys'),
      fetchAPI('/integrations/services/configured'),
    ])
    if (!provRes.error && provRes.data?.providers) setProviders(provRes.data.providers)
    if (!keysRes.error && keysRes.data?.keys) {
      const map = {}
      keysRes.data.keys.forEach((k) => { map[k.provider] = k })
      setSavedKeys(map)
    }
    if (!svcRes.error && svcRes.data?.services) {
      setServices(svcRes.data.services)
    } else {
      // Fallback: load unconfigured list from /services
      const fallback = await fetchAPI('/integrations/services')
      if (!fallback.error && fallback.data?.services) setServices(fallback.data.services)
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleKeySaved = (providerId) => {
    fetchAPI('/integrations/providers/keys').then((res) => {
      if (!res.error && res.data?.keys) {
        const map = {}
        res.data.keys.forEach((k) => { map[k.provider] = k })
        setSavedKeys(map)
      }
    })
  }

  const handleServiceSaved = (serviceId) => {
    setServices((prev) => prev.map((s) => s.id === serviceId ? { ...s, configured: true } : s))
  }

  const configuredCount = services.filter((s) => s.configured).length
  const keyCount = Object.keys(savedKeys).length

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
        <span style={{ fontSize: 14, color: '#9CA3AF' }}>Loading integrations…</span>
      </div>
    )
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out', maxWidth: 900 }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          Integrations
        </h1>
        <p style={{ fontSize: 14, color: '#9CA3AF' }}>
          Connect LLM providers and external services to power your workflows.
        </p>
        <div style={{ display: 'flex', gap: 16, marginTop: 12 }}>
          <span style={{ fontSize: 13, color: '#6B7280' }}>
            <strong style={{ color: '#6366F1' }}>{keyCount}</strong> LLM key{keyCount !== 1 ? 's' : ''} configured
          </span>
          <span style={{ fontSize: 13, color: '#6B7280' }}>
            <strong style={{ color: '#059669' }}>{configuredCount}</strong> service{configuredCount !== 1 ? 's' : ''} connected
          </span>
        </div>
      </div>

      {/* LLM Providers */}
      <section style={{ marginBottom: 40 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366F1" strokeWidth="2" strokeLinecap="round">
            <path d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5" />
          </svg>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: '#111827', margin: 0 }}>LLM Providers</h2>
          <span style={{ fontSize: 12, color: '#9CA3AF' }}>Add your API keys to use your own quota</span>
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(280px, 100%), 1fr))',
          gap: 16,
        }}>
          {providers.map((p) => (
            <ProviderCard
              key={p.id}
              provider={p}
              savedKey={savedKeys[p.id] || null}
              onSaved={handleKeySaved}
            />
          ))}
        </div>
      </section>

      {/* Service Integrations */}
      <section>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2" strokeLinecap="round">
            <path d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
          </svg>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: '#111827', margin: 0 }}>Service Integrations</h2>
          <span style={{ fontSize: 12, color: '#9CA3AF' }}>Click a card to configure</span>
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(320px, 100%), 1fr))',
          gap: 12,
        }}>
          {services.map((s) => (
            <ServiceCard key={s.id} service={{...s, _lang: lang}} onSaved={handleServiceSaved} />
          ))}
        </div>
      </section>
    </div>
  )
}
