import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

const ICONS = ['⚡', '📊', '🔄', '📧', '📄', '🤖', '🔍', '💰', '🏢', '🐝', '🧠', '🔗']
const COLORS = ['#6366F1', '#10B981', '#F59E0B', '#EC4899', '#3B82F6', '#8B5CF6', '#EF4444', '#0891B2']
const INPUT_TYPES = ['none', 'text', 'form', 'json']

const inputStyle = {
  width: '100%', padding: '8px 12px', borderRadius: 8,
  border: '1px solid #E5E7EB', fontSize: 13, color: '#111827',
  background: '#fff', boxSizing: 'border-box', outline: 'none',
}

export default function PublishModal({ onClose, onPublished, lang = 'en' }) {
  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  // configStep: 'appearance' | 'trigger' | 'input'
  const [configStep, setConfigStep] = useState('appearance')
  const [form, setForm] = useState({
    name: '', description: '', icon: '⚡', color: '#6366F1',
    trigger_type: 'manual', schedule_cron: '',
    input_config: { type: 'none' },
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchAPI('/workflows/').then(res => {
      if (!res.error && res.data) {
        const list = Array.isArray(res.data) ? res.data : res.data.workflows || []
        setWorkflows(list.filter(w => w.status === 'active' || w.status === 'draft'))
      }
      setLoading(false)
    })
  }, [])

  const handleSelect = (wf) => {
    setSelected(wf)
    setForm(f => ({ ...f, name: wf.name || '', description: wf.description || '' }))
    setConfigStep('appearance')
  }

  const handlePublish = async () => {
    if (!selected) return
    setSaving(true)
    setError(null)
    const res = await fetchAPI('/automations/', {
      method: 'POST',
      body: JSON.stringify({
        workflow_id: selected.id,
        name: form.name,
        description: form.description,
        icon: form.icon,
        color: form.color,
        trigger_type: form.trigger_type,
        schedule_cron: form.trigger_type === 'schedule' ? form.schedule_cron : null,
        input_config: form.input_config,
      }),
    })
    setSaving(false)
    if (res.error) { setError(res.error); return }
    onPublished && onPublished()
    onClose()
  }

  const setInputConfig = (patch) => setForm(f => ({ ...f, input_config: { ...f.input_config, ...patch } }))

  const addFormField = () => {
    const fields = form.input_config.fields || []
    setInputConfig({ fields: [...fields, { key: `field_${fields.length + 1}`, label: '', type: 'text' }] })
  }

  const updateField = (i, patch) => {
    const fields = [...(form.input_config.fields || [])]
    fields[i] = { ...fields[i], ...patch }
    setInputConfig({ fields })
  }

  const removeField = (i) => {
    const fields = (form.input_config.fields || []).filter((_, idx) => idx !== i)
    setInputConfig({ fields })
  }

  const STEPS = [
    { key: 'appearance', label: lang === 'es' ? 'Apariencia' : 'Appearance' },
    { key: 'trigger', label: lang === 'es' ? 'Disparo' : 'Trigger' },
    { key: 'input', label: lang === 'es' ? 'Entrada' : 'Input' },
  ]

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 100, backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#fff', borderRadius: 16, padding: 28,
        width: '90%', maxWidth: 600, maxHeight: '90vh', overflowY: 'auto',
        border: '1px solid #E5E7EB', boxShadow: '0 24px 48px rgba(0,0,0,0.2)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: '#111827', margin: 0 }}>
            {lang === 'es' ? 'Publicar Automatización' : 'Publish Automation'}
          </h2>
          <button onClick={onClose} style={{ background: '#F3F4F6', border: 'none', borderRadius: 8, width: 32, height: 32, cursor: 'pointer', fontSize: 16, color: '#6B7280' }}>✕</button>
        </div>

        {/* Step 1: pick workflow */}
        {!selected ? (
          <>
            <p style={{ fontSize: 13, color: '#6B7280', marginBottom: 16 }}>
              {lang === 'es' ? 'Selecciona un workflow para publicar:' : 'Select a workflow to publish:'}
            </p>
            {loading ? (
              <div style={{ padding: 24, textAlign: 'center', color: '#9CA3AF' }}>
                {lang === 'es' ? 'Cargando...' : 'Loading...'}
              </div>
            ) : workflows.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
                {lang === 'es' ? 'No hay workflows activos. Crea uno en el Builder primero.' : 'No active workflows. Create one in the Builder first.'}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {workflows.map(wf => (
                  <div key={wf.id} onClick={() => handleSelect(wf)} style={{
                    padding: '12px 16px', borderRadius: 10, border: '1px solid #E5E7EB',
                    cursor: 'pointer', transition: 'all 0.15s',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = '#6366F1'}
                    onMouseLeave={e => e.currentTarget.style.borderColor = '#E5E7EB'}
                  >
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{wf.name}</div>
                      <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 2 }}>
                        {wf.dag_definition?.steps?.length || 0} {lang === 'es' ? 'pasos' : 'steps'} · {wf.status}
                      </div>
                    </div>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round">
                      <path d="M5 12h14m-7-7l7 7-7 7" />
                    </svg>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <>
            {/* Workflow badge */}
            <div style={{ padding: '8px 12px', borderRadius: 8, background: '#EEF2FF', marginBottom: 20, fontSize: 13, color: '#4338CA' }}>
              {lang === 'es' ? 'Workflow:' : 'Workflow:'} <strong>{selected.name}</strong>
              <button onClick={() => setSelected(null)} style={{ marginLeft: 8, background: 'none', border: 'none', color: '#6366F1', cursor: 'pointer', fontSize: 12 }}>
                {lang === 'es' ? 'cambiar' : 'change'}
              </button>
            </div>

            {/* Step tabs */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '2px solid #E5E7EB' }}>
              {STEPS.map(s => (
                <button key={s.key} onClick={() => setConfigStep(s.key)} style={{
                  padding: '7px 14px', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600,
                  background: 'none', color: configStep === s.key ? '#6366F1' : '#9CA3AF',
                  borderBottom: configStep === s.key ? '2px solid #6366F1' : '2px solid transparent',
                  marginBottom: -2,
                }}>{s.label}</button>
              ))}
            </div>

            {/* Appearance */}
            {configStep === 'appearance' && (
              <>
                <div style={{ marginBottom: 14 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>{lang === 'es' ? 'Nombre' : 'Name'}</label>
                  <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} style={inputStyle} />
                </div>
                <div style={{ marginBottom: 14 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>{lang === 'es' ? 'Descripción' : 'Description'}</label>
                  <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={2} style={{ ...inputStyle, resize: 'vertical' }} />
                </div>
                <div style={{ marginBottom: 14 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>{lang === 'es' ? 'Ícono' : 'Icon'}</label>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {ICONS.map(ic => (
                      <button key={ic} onClick={() => setForm(f => ({ ...f, icon: ic }))} style={{
                        width: 36, height: 36, borderRadius: 8, border: `2px solid ${form.icon === ic ? '#6366F1' : '#E5E7EB'}`,
                        background: form.icon === ic ? '#EEF2FF' : '#F9FAFB', fontSize: 18, cursor: 'pointer',
                      }}>{ic}</button>
                    ))}
                  </div>
                </div>
                <div style={{ marginBottom: 20 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>{lang === 'es' ? 'Color' : 'Color'}</label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {COLORS.map(c => (
                      <button key={c} onClick={() => setForm(f => ({ ...f, color: c }))} style={{
                        width: 28, height: 28, borderRadius: '50%', background: c,
                        border: `3px solid ${form.color === c ? '#111827' : 'transparent'}`, cursor: 'pointer',
                      }} />
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Trigger */}
            {configStep === 'trigger' && (
              <div style={{ marginBottom: 20 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 8 }}>
                  {lang === 'es' ? 'Tipo de disparo' : 'Trigger type'}
                </label>
                <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                  {['manual', 'schedule', 'webhook'].map(t => (
                    <button key={t} onClick={() => setForm(f => ({ ...f, trigger_type: t }))} style={{
                      padding: '8px 16px', borderRadius: 8,
                      border: `1px solid ${form.trigger_type === t ? '#6366F1' : '#E5E7EB'}`,
                      background: form.trigger_type === t ? '#EEF2FF' : '#F9FAFB',
                      color: form.trigger_type === t ? '#6366F1' : '#6B7280',
                      fontSize: 13, fontWeight: 600, cursor: 'pointer', textTransform: 'capitalize',
                    }}>{t}</button>
                  ))}
                </div>
                {form.trigger_type === 'schedule' && (
                  <div>
                    <label style={{ fontSize: 12, color: '#6B7280', display: 'block', marginBottom: 6 }}>
                      Cron {lang === 'es' ? '(ej: "0 9 * * 1-5" = lunes-viernes 9am)' : '(e.g. "0 9 * * 1-5" = weekdays 9am)'}
                    </label>
                    <input value={form.schedule_cron} onChange={e => setForm(f => ({ ...f, schedule_cron: e.target.value }))}
                      placeholder="0 9 * * 1-5" style={inputStyle} />
                  </div>
                )}
                {form.trigger_type === 'webhook' && (
                  <p style={{ fontSize: 12, color: '#9CA3AF', padding: '8px 12px', background: '#F9FAFB', borderRadius: 8 }}>
                    {lang === 'es'
                      ? 'Se generará una URL única. Cualquier POST a esa URL ejecutará la automatización con el body como input.'
                      : 'A unique URL will be generated. Any POST to that URL will execute the automation with the body as input.'}
                  </p>
                )}
              </div>
            )}

            {/* Input config */}
            {configStep === 'input' && (
              <div style={{ marginBottom: 20 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 8 }}>
                  {lang === 'es' ? 'Tipo de entrada' : 'Input type'}
                </label>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
                  {INPUT_TYPES.map(t => (
                    <button key={t} onClick={() => setInputConfig({ type: t })} style={{
                      padding: '7px 14px', borderRadius: 8,
                      border: `1px solid ${form.input_config.type === t ? '#6366F1' : '#E5E7EB'}`,
                      background: form.input_config.type === t ? '#EEF2FF' : '#F9FAFB',
                      color: form.input_config.type === t ? '#6366F1' : '#6B7280',
                      fontSize: 12, fontWeight: 600, cursor: 'pointer', textTransform: 'capitalize',
                    }}>{t === 'none' ? (lang === 'es' ? 'Ninguno' : 'None') : t}</button>
                  ))}
                </div>

                {form.input_config.type === 'text' && (
                  <>
                    <div style={{ marginBottom: 10 }}>
                      <label style={{ fontSize: 12, color: '#6B7280', display: 'block', marginBottom: 4 }}>{lang === 'es' ? 'Etiqueta' : 'Label'}</label>
                      <input value={form.input_config.label || ''} onChange={e => setInputConfig({ label: e.target.value })} style={inputStyle} placeholder={lang === 'es' ? 'Texto a analizar' : 'Text to analyze'} />
                    </div>
                    <div>
                      <label style={{ fontSize: 12, color: '#6B7280', display: 'block', marginBottom: 4 }}>Placeholder</label>
                      <input value={form.input_config.placeholder || ''} onChange={e => setInputConfig({ placeholder: e.target.value })} style={inputStyle} placeholder={lang === 'es' ? 'Pega tu texto aquí...' : 'Paste your text here...'} />
                    </div>
                  </>
                )}

                {form.input_config.type === 'json' && (
                  <div>
                    <label style={{ fontSize: 12, color: '#6B7280', display: 'block', marginBottom: 4 }}>{lang === 'es' ? 'Etiqueta' : 'Label'}</label>
                    <input value={form.input_config.label || ''} onChange={e => setInputConfig({ label: e.target.value })} style={inputStyle} placeholder="JSON" />
                  </div>
                )}

                {form.input_config.type === 'form' && (
                  <div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                      {(form.input_config.fields || []).map((field, i) => (
                        <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                          <input value={field.key} onChange={e => updateField(i, { key: e.target.value })}
                            placeholder="key" style={{ ...inputStyle, flex: 1 }} />
                          <input value={field.label} onChange={e => updateField(i, { label: e.target.value })}
                            placeholder={lang === 'es' ? 'etiqueta' : 'label'} style={{ ...inputStyle, flex: 1 }} />
                          <select value={field.type} onChange={e => updateField(i, { type: e.target.value })}
                            style={{ ...inputStyle, width: 90 }}>
                            {['text', 'textarea', 'select', 'number'].map(t => <option key={t} value={t}>{t}</option>)}
                          </select>
                          <button onClick={() => removeField(i)} style={{ background: 'none', border: 'none', color: '#EF4444', cursor: 'pointer', fontSize: 16, padding: '0 4px' }}>✕</button>
                        </div>
                      ))}
                    </div>
                    <button onClick={addFormField} style={{
                      padding: '6px 12px', borderRadius: 7, border: '1px dashed #6366F1',
                      background: '#EEF2FF', color: '#6366F1', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                    }}>
                      + {lang === 'es' ? 'Agregar campo' : 'Add field'}
                    </button>
                  </div>
                )}
              </div>
            )}

            {error && (
              <div style={{ padding: '8px 12px', borderRadius: 8, background: 'rgba(239,68,68,0.08)', color: '#DC2626', fontSize: 13, marginBottom: 12 }}>
                {error}
              </div>
            )}

            <button onClick={handlePublish} disabled={saving || !form.name.trim()} style={{
              width: '100%', padding: '11px 0', borderRadius: 9, border: 'none',
              background: saving ? '#A5B4FC' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              color: '#fff', fontSize: 14, fontWeight: 600, cursor: saving ? 'default' : 'pointer',
            }}>
              {saving
                ? (lang === 'es' ? 'Publicando...' : 'Publishing...')
                : (lang === 'es' ? 'Publicar Automatización' : 'Publish Automation')}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
