import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'
import { useIsMobile } from '../../shared/hooks/useIsMobile'

const TYPE_COLORS = {
  classifier: '#818CF8', extractor: '#10B981', summarizer: '#F59E0B',
  generator: '#A78BFA', router: '#EC4899', loader: '#60A5FA',
  storage: '#34D399', validator: '#FB923C',
}

const MODELS_BY_PROVIDER = {
  groq: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'],
  claude: ['claude-sonnet-4-20250514', 'claude-haiku-4-5-20251001'],
  openai: ['gpt-4o', 'gpt-4o-mini'],
  'openai-gpt4o': ['gpt-4o'],
}

const ALL_TOOLS = ['llm_chat', 'regex', 'web_search', 'rag_search', 'statistics', 'template_engine', 'config_editor']

const label = (en, es, lang) => lang === 'es' ? es : en

function TestAgentSection({ agentType, lang }) {
  const [testInput, setTestInput] = useState('')
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  const handleTest = async () => {
    if (!testInput.trim()) return
    setTesting(true)
    setTestResult(null)
    const { fetchAPI } = await import('../../services/api')
    const res = await fetchAPI('/demo/analyze', {
      method: 'POST',
      body: JSON.stringify({ text: testInput }),
    })
    setTesting(false)
    setTestResult(res.data || res.error || 'No response')
  }

  return (
    <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #F3F4F6' }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 8 }}>
        {lang === 'es' ? 'Probar Agente' : 'Test Agent'}
      </div>
      <textarea
        value={testInput}
        onChange={e => setTestInput(e.target.value)}
        placeholder={lang === 'es' ? 'Texto de prueba...' : 'Test input text...'}
        rows={3}
        style={{
          width: '100%', padding: 10, borderRadius: 8, border: '1px solid #E5E7EB',
          fontSize: 13, resize: 'vertical', outline: 'none', boxSizing: 'border-box', marginBottom: 8,
        }}
      />
      <button onClick={handleTest} disabled={testing || !testInput.trim()} style={{
        padding: '7px 16px', borderRadius: 7, border: 'none', fontSize: 13, fontWeight: 600,
        background: testing ? '#A5B4FC' : '#F59E0B', color: '#fff',
        cursor: testing ? 'default' : 'pointer', marginBottom: 8,
      }}>
        {testing ? '...' : (lang === 'es' ? 'Probar' : 'Test')}
      </button>
      {testResult && (
        <pre style={{
          fontSize: 11, background: '#F9FAFB', borderRadius: 8, padding: 10,
          border: '1px solid #E5E7EB', maxHeight: 150, overflow: 'auto',
          whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#374151',
        }}>
          {typeof testResult === 'object' ? JSON.stringify(testResult, null, 2) : String(testResult)}
        </pre>
      )}
    </div>
  )
}

export default function AgentDetailPanel({ agent, onClose, lang = 'en' }) {
  const isMobile = useIsMobile()
  const [tab, setTab] = useState('config')
  const [cfg, setCfg] = useState(null)
  const [availableProviders, setAvailableProviders] = useState([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)

  // Load config + available providers on open
  useEffect(() => {
    if (!agent) return
    setSaved(false)
    setError(null)

    fetchAPI(`/agents/${agent.type}/config`).then(res => {
      if (!res.error && res.data) {
        setCfg(res.data)
      } else {
        // fallback defaults
        setCfg({
          provider: 'groq', model: 'llama-3.3-70b-versatile',
          temperature: 0.3, max_tokens: 1024,
          system_prompt: '', tools: agent.tools || [], status: 'active',
        })
      }
    })

    fetchAPI('/integrations/providers/keys').then(res => {
      if (!res.error && res.data?.keys) {
        setAvailableProviders(res.data.keys.map(k => k.provider))
      }
    })
  }, [agent?.type])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    const res = await fetchAPI(`/agents/${agent.type}/config`, {
      method: 'PUT',
      body: JSON.stringify(cfg),
    })
    setSaving(false)
    if (res.error) {
      setError(res.error)
    } else {
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    }
  }

  if (!agent) return null

  const typeColor = TYPE_COLORS[agent.type] || '#818CF8'
  const models = MODELS_BY_PROVIDER[cfg?.provider] || []

  const inputStyle = {
    width: '100%', padding: '8px 12px', borderRadius: 8,
    border: '1px solid #E5E7EB', fontSize: 13, color: '#111827',
    background: '#fff', boxSizing: 'border-box',
    outline: 'none',
  }
  const labelStyle = { fontSize: 12, fontWeight: 600, color: '#6B7280', marginBottom: 6, display: 'block' }
  const fieldStyle = { marginBottom: 16 }

  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: 24, animation: 'fadeIn 0.2s ease-out',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: '#111827', margin: 0 }}>{agent.name}</h2>
            <span style={{
              fontSize: 11, padding: '3px 10px', borderRadius: 6,
              background: `${typeColor}20`, color: typeColor, fontWeight: 600,
            }}>{agent.type}</span>
          </div>
          <p style={{ fontSize: 13, color: '#6B7280', margin: 0 }}>{agent.description}</p>
        </div>
        <button
          onClick={onClose}
          aria-label="Close"
          style={{
            background: '#F3F4F6', border: 'none', borderRadius: 8,
            width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: '#9CA3AF', flexShrink: 0,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '2px solid #E5E7EB' }}>
        {[
          { key: 'config', label: label('Configure', 'Configurar', lang) },
          { key: 'info', label: label('Info & Stats', 'Info y Stats', lang) },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '8px 16px', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600,
            background: 'none', color: tab === t.key ? '#6366F1' : '#9CA3AF',
            borderBottom: tab === t.key ? '2px solid #6366F1' : '2px solid transparent',
            marginBottom: -2, transition: 'all 0.15s',
          }}>{t.label}</button>
        ))}
      </div>

      {/* Config Tab */}
      {tab === 'config' && cfg && (
        <div>
          {/* Provider */}
          <div style={fieldStyle}>
            <label style={labelStyle}>{label('LLM Provider', 'Proveedor LLM', lang)}</label>
            {availableProviders.length === 0 && (
              <p style={{ fontSize: 12, color: '#F59E0B', marginBottom: 8 }}>
                {label(
                  'No API keys configured. Go to Integrations → LLM Providers to add keys.',
                  'Sin claves API. Ve a Integraciones → Proveedores LLM para agregar.',
                  lang
                )}
              </p>
            )}
            <select
              value={cfg.provider}
              onChange={e => setCfg(prev => ({
                ...prev,
                provider: e.target.value,
                model: (MODELS_BY_PROVIDER[e.target.value] || [])[0] || prev.model,
              }))}
              style={inputStyle}
            >
              {['groq', 'claude', 'openai', 'openai-gpt4o'].map(p => (
                <option key={p} value={p} disabled={availableProviders.length > 0 && !availableProviders.includes(p)}>
                  {p}{availableProviders.includes(p) ? ' ✓' : availableProviders.length > 0 ? ' (no key)' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Model */}
          <div style={fieldStyle}>
            <label style={labelStyle}>{label('Model', 'Modelo', lang)}</label>
            <select value={cfg.model} onChange={e => setCfg(prev => ({ ...prev, model: e.target.value }))} style={inputStyle}>
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          {/* Temperature + Max Tokens side by side */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
            <div style={{ flex: 1 }}>
              <label style={labelStyle}>
                {label('Temperature', 'Temperatura', lang)}: <strong>{cfg.temperature}</strong>
              </label>
              <input
                type="range" min="0" max="1" step="0.05"
                value={cfg.temperature}
                onChange={e => setCfg(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                style={{ width: '100%', accentColor: '#6366F1' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#9CA3AF' }}>
                <span>{label('Precise', 'Preciso', lang)}</span>
                <span>{label('Creative', 'Creativo', lang)}</span>
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <label style={labelStyle}>{label('Max Tokens', 'Tokens Máx.', lang)}</label>
              <input
                type="number" min="64" max="16000" step="64"
                value={cfg.max_tokens}
                onChange={e => setCfg(prev => ({ ...prev, max_tokens: parseInt(e.target.value) || 1024 }))}
                style={inputStyle}
              />
            </div>
          </div>

          {/* System Prompt */}
          <div style={fieldStyle}>
            <label style={labelStyle}>{label('System Prompt', 'Prompt del Sistema', lang)}</label>
            <textarea
              value={cfg.system_prompt || ''}
              onChange={e => setCfg(prev => ({ ...prev, system_prompt: e.target.value }))}
              placeholder={label('Override the default system prompt...', 'Sobreescribir el prompt del sistema...', lang)}
              rows={5}
              style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace', lineHeight: 1.5 }}
            />
          </div>

          {/* Tools */}
          <div style={fieldStyle}>
            <label style={labelStyle}>{label('Tools', 'Herramientas', lang)}</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {ALL_TOOLS.map(tool => {
                const active = cfg.tools?.includes(tool)
                return (
                  <label key={tool} style={{
                    display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
                    padding: '5px 10px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                    border: `1px solid ${active ? '#6366F1' : '#E5E7EB'}`,
                    background: active ? 'rgba(99,102,241,0.08)' : '#F9FAFB',
                    color: active ? '#6366F1' : '#6B7280',
                    transition: 'all 0.15s',
                  }}>
                    <input
                      type="checkbox"
                      checked={active}
                      onChange={() => setCfg(prev => ({
                        ...prev,
                        tools: active
                          ? prev.tools.filter(t => t !== tool)
                          : [...(prev.tools || []), tool],
                      }))}
                      style={{ accentColor: '#6366F1' }}
                    />
                    {tool}
                  </label>
                )
              })}
            </div>
          </div>

          {/* Status toggle */}
          <div style={{ ...fieldStyle, display: 'flex', alignItems: 'center', gap: 12 }}>
            <label style={{ ...labelStyle, margin: 0 }}>{label('Status', 'Estado', lang)}</label>
            <button
              onClick={() => setCfg(prev => ({ ...prev, status: prev.status === 'active' ? 'inactive' : 'active' }))}
              style={{
                padding: '5px 14px', borderRadius: 20, border: 'none', cursor: 'pointer',
                fontSize: 12, fontWeight: 600, transition: 'all 0.15s',
                background: cfg.status === 'active' ? 'rgba(16,185,129,0.1)' : 'rgba(156,163,175,0.1)',
                color: cfg.status === 'active' ? '#10B981' : '#9CA3AF',
              }}
            >
              {cfg.status === 'active'
                ? label('Active', 'Activo', lang)
                : label('Inactive', 'Inactivo', lang)}
            </button>
          </div>

          {/* Error */}
          {error && (
            <div style={{
              padding: '10px 14px', borderRadius: 8, marginBottom: 12, fontSize: 13,
              background: 'rgba(239,68,68,0.08)', color: '#DC2626', border: '1px solid rgba(239,68,68,0.2)',
            }}>
              {error}
            </div>
          )}

          {/* Save */}
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              width: '100%', padding: '10px 0', borderRadius: 9, border: 'none',
              fontSize: 14, fontWeight: 600, cursor: saving ? 'default' : 'pointer',
              background: saved ? '#10B981' : saving ? '#A5B4FC' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              color: '#fff', transition: 'all 0.2s',
              boxShadow: saving || saved ? 'none' : '0 2px 8px rgba(99,102,241,0.3)',
            }}
          >
            {saved
              ? label('✓ Saved', '✓ Guardado', lang)
              : saving
                ? label('Saving...', 'Guardando...', lang)
                : label('Save Configuration', 'Guardar Configuración', lang)}
          </button>

          {/* Quick test */}
          <TestAgentSection agentType={agent.agent_type || agent.type} lang={lang} />
        </div>
      )}

      {/* Info Tab */}
      {tab === 'info' && (
        <div>
          {/* Tools */}
          {agent.tools?.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 8 }}>
                {label('Default Tools', 'Herramientas por Defecto', lang)}
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {agent.tools.map(tool => (
                  <span key={tool} style={{
                    fontSize: 12, padding: '4px 10px', borderRadius: 6,
                    background: 'rgba(99,102,241,0.1)', color: '#6366F1', fontWeight: 500,
                  }}>{tool}</span>
                ))}
              </div>
            </div>
          )}

          {/* Stats */}
          {agent.stats && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 10 }}>
                {label('Statistics', 'Estadísticas', lang)}
              </div>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: isMobile ? 6 : 12,
              }}>
                {[
                  { label: label('Runs', 'Ejecuciones', lang), value: agent.stats.total_runs?.toLocaleString() || '0' },
                  { label: label('Avg Duration', 'Duración Prom.', lang), value: agent.stats.avg_duration ? `${(agent.stats.avg_duration / 1000).toFixed(1)}s` : '--' },
                  { label: label('Success', 'Éxito', lang), value: agent.stats.success_rate != null ? `${(agent.stats.success_rate * 100).toFixed(0)}%` : '--', color: '#10B981' },
                ].map(s => (
                  <div key={s.label} style={{
                    background: '#F9FAFB', borderRadius: 8, padding: 12, textAlign: 'center',
                    border: '1px solid #E5E7EB',
                  }}>
                    <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4 }}>{s.label}</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: s.color || '#111827' }}>{s.value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Current active config summary */}
          {cfg?.is_custom && (
            <div style={{
              padding: 14, borderRadius: 8, background: 'rgba(99,102,241,0.06)',
              border: '1px solid rgba(99,102,241,0.2)', fontSize: 13, color: '#374151',
            }}>
              <strong style={{ color: '#6366F1' }}>{label('Custom config active:', 'Config personalizada activa:', lang)}</strong>
              {' '}{cfg.provider} / {cfg.model} / temp {cfg.temperature}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
