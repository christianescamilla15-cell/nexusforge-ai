import { useState, useEffect, useCallback } from 'react'
import { fetchAPI } from '../../services/api'

// ── Constants ─────────────────────────────────────────────────────────────────

const OPERATORS = [
  { value: 'equals', label: '= equals' },
  { value: 'not_equals', label: '!= not equals' },
  { value: 'contains', label: 'contains' },
  { value: 'greater_than', label: '> greater than' },
  { value: 'less_than', label: '< less than' },
  { value: 'starts_with', label: 'starts with' },
  { value: 'is_empty', label: 'is empty' },
  { value: 'is_not_empty', label: 'is not empty' },
  { value: 'regex', label: 'matches regex' },
]

const ACTION_TYPES = [
  { value: 'notify', label: 'Notify' },
  { value: 'route', label: 'Route to agent' },
  { value: 'set_field', label: 'Set field' },
  { value: 'skip_step', label: 'Skip step' },
]

const OP_SYMBOLS = {
  equals: '=', not_equals: '!=', contains: 'contains',
  greater_than: '>', less_than: '<', starts_with: 'starts with',
  is_empty: 'is empty', is_not_empty: 'is not empty', regex: '~',
}

const NO_VALUE_OPS = ['is_empty', 'is_not_empty']

const t = (lang, en, es) => lang === 'es' ? es : en

// ── Styles ────────────────────────────────────────────────────────────────────

const card = {
  background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
  padding: 16, marginBottom: 12,
}
const pill = (color = '#6366F1') => ({
  display: 'inline-flex', alignItems: 'center', gap: 4,
  padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 500,
  background: `${color}14`, color, border: `1px solid ${color}30`,
})
const badge = (color = '#10B981') => ({
  display: 'inline-flex', alignItems: 'center', gap: 4,
  padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
  background: `${color}14`, color, textTransform: 'uppercase',
})
const btn = (bg = '#6366F1', fg = '#fff') => ({
  padding: '7px 16px', borderRadius: 8, border: 'none', fontSize: 13,
  fontWeight: 600, background: bg, color: fg, cursor: 'pointer',
})
const btnSmall = (bg = '#F3F4F6', fg = '#374151') => ({
  padding: '4px 10px', borderRadius: 6, border: 'none', fontSize: 12,
  fontWeight: 500, background: bg, color: fg, cursor: 'pointer',
})
const input = {
  padding: '6px 10px', borderRadius: 6, border: '1px solid #D1D5DB',
  fontSize: 13, outline: 'none', background: '#FAFAFA',
}
const select = { ...input, background: '#FAFAFA', cursor: 'pointer' }

// ── Sub-components ────────────────────────────────────────────────────────────

function ConditionPills({ conditions }) {
  if (!conditions || conditions.length === 0) return <span style={{ color: '#9CA3AF', fontSize: 12 }}>No conditions</span>
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {conditions.map((c, i) => (
        <span key={i}>
          {i > 0 && <span style={{ fontSize: 11, color: '#9CA3AF', marginRight: 6 }}>AND</span>}
          <span style={pill('#6366F1')}>
            {c.field} {OP_SYMBOLS[c.operator] || c.operator} {NO_VALUE_OPS.includes(c.operator) ? '' : c.value}
          </span>
        </span>
      ))}
    </div>
  )
}

function ActionBadges({ actions }) {
  if (!actions || actions.length === 0) return <span style={{ color: '#9CA3AF', fontSize: 12 }}>No actions</span>
  const colorMap = { notify: '#F59E0B', route: '#8B5CF6', set_field: '#10B981', skip_step: '#EF4444' }
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {actions.map((a, i) => (
        <span key={i} style={badge(colorMap[a.type] || '#6B7280')}>
          {a.type === 'notify' && `Notify ${a.channel || ''}`}
          {a.type === 'route' && `Route: ${a.target_agent || ''}`}
          {a.type === 'set_field' && `Set ${a.field || ''} = ${a.value || ''}`}
          {a.type === 'skip_step' && `Skip: ${a.step_name || ''}`}
        </span>
      ))}
    </div>
  )
}

function ConditionEditor({ conditions, onChange }) {
  const add = () => onChange([...conditions, { field: '', operator: 'equals', value: '' }])
  const remove = (i) => onChange(conditions.filter((_, j) => j !== i))
  const update = (i, key, val) => {
    const next = [...conditions]
    next[i] = { ...next[i], [key]: val }
    onChange(next)
  }
  return (
    <div>
      {conditions.map((c, i) => (
        <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {i > 0 && <span style={{ fontSize: 11, color: '#9CA3AF', fontWeight: 600, width: 32 }}>AND</span>}
          {i === 0 && <span style={{ fontSize: 11, color: '#9CA3AF', fontWeight: 600, width: 32 }}>IF</span>}
          <input style={{ ...input, flex: '1 1 120px', minWidth: 100 }} placeholder="field"
            value={c.field} onChange={e => update(i, 'field', e.target.value)} />
          <select style={{ ...select, flex: '0 0 150px' }} value={c.operator}
            onChange={e => update(i, 'operator', e.target.value)}>
            {OPERATORS.map(op => <option key={op.value} value={op.value}>{op.label}</option>)}
          </select>
          {!NO_VALUE_OPS.includes(c.operator) && (
            <input style={{ ...input, flex: '1 1 120px', minWidth: 80 }} placeholder="value"
              value={c.value} onChange={e => update(i, 'value', e.target.value)} />
          )}
          <button style={{ ...btnSmall('#FEE2E2', '#DC2626'), flexShrink: 0 }} onClick={() => remove(i)}>x</button>
        </div>
      ))}
      <button style={btnSmall('#EEF2FF', '#6366F1')} onClick={add}>+ Condition</button>
    </div>
  )
}

function ActionEditor({ actions, onChange }) {
  const add = () => onChange([...actions, { type: 'notify', channel: '', message: '' }])
  const remove = (i) => onChange(actions.filter((_, j) => j !== i))
  const update = (i, key, val) => {
    const next = [...actions]
    next[i] = { ...next[i], [key]: val }
    onChange(next)
  }
  return (
    <div>
      {actions.map((a, i) => (
        <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, color: '#9CA3AF', fontWeight: 600, width: 40 }}>THEN</span>
          <select style={{ ...select, flex: '0 0 130px' }} value={a.type}
            onChange={e => update(i, 'type', e.target.value)}>
            {ACTION_TYPES.map(at => <option key={at.value} value={at.value}>{at.label}</option>)}
          </select>
          {a.type === 'notify' && (
            <>
              <input style={{ ...input, flex: '0 0 100px' }} placeholder="channel" value={a.channel || ''}
                onChange={e => update(i, 'channel', e.target.value)} />
              <input style={{ ...input, flex: '1 1 180px', minWidth: 120 }} placeholder="message" value={a.message || ''}
                onChange={e => update(i, 'message', e.target.value)} />
            </>
          )}
          {a.type === 'route' && (
            <input style={{ ...input, flex: '1 1 180px' }} placeholder="target_agent" value={a.target_agent || ''}
              onChange={e => update(i, 'target_agent', e.target.value)} />
          )}
          {a.type === 'set_field' && (
            <>
              <input style={{ ...input, flex: '0 0 120px' }} placeholder="field" value={a.field || ''}
                onChange={e => update(i, 'field', e.target.value)} />
              <input style={{ ...input, flex: '1 1 120px' }} placeholder="value" value={a.value || ''}
                onChange={e => update(i, 'value', e.target.value)} />
            </>
          )}
          {a.type === 'skip_step' && (
            <input style={{ ...input, flex: '1 1 180px' }} placeholder="step_name" value={a.step_name || ''}
              onChange={e => update(i, 'step_name', e.target.value)} />
          )}
          <button style={{ ...btnSmall('#FEE2E2', '#DC2626'), flexShrink: 0 }} onClick={() => remove(i)}>x</button>
        </div>
      ))}
      <button style={btnSmall('#ECFDF5', '#10B981')} onClick={add}>+ Action</button>
    </div>
  )
}

// ── Inline Rule Editor ────────────────────────────────────────────────────────

function RuleEditor({ rule, onSave, onCancel, lang }) {
  const [name, setName] = useState(rule?.name || '')
  const [description, setDescription] = useState(rule?.description || '')
  const [priority, setPriority] = useState(rule?.priority ?? 0)
  const [conditions, setConditions] = useState(rule?.conditions || [])
  const [actions, setActions] = useState(rule?.actions || [])
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!name.trim()) return
    setSaving(true)
    await onSave({ name, description, priority, conditions, actions })
    setSaving(false)
  }

  return (
    <div style={{ ...card, border: '2px solid #6366F1', background: '#FAFBFF' }}>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 200px' }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 4 }}>
            {t(lang, 'Rule name', 'Nombre de la regla')}
          </label>
          <input style={{ ...input, width: '100%' }} value={name} onChange={e => setName(e.target.value)}
            placeholder={t(lang, 'e.g. High urgency escalation', 'ej. Escalamiento urgencia alta')} />
        </div>
        <div style={{ flex: '1 1 200px' }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 4 }}>
            {t(lang, 'Description', 'Descripcion')}
          </label>
          <input style={{ ...input, width: '100%' }} value={description} onChange={e => setDescription(e.target.value)}
            placeholder={t(lang, 'Optional description', 'Descripcion opcional')} />
        </div>
        <div style={{ flex: '0 0 80px' }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 4 }}>
            {t(lang, 'Priority', 'Prioridad')}
          </label>
          <input style={{ ...input, width: '100%' }} type="number" value={priority}
            onChange={e => setPriority(parseInt(e.target.value) || 0)} />
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, fontWeight: 700, color: '#374151', display: 'block', marginBottom: 8 }}>
          {t(lang, 'Conditions (ALL must match)', 'Condiciones (TODAS deben cumplirse)')}
        </label>
        <ConditionEditor conditions={conditions} onChange={setConditions} />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, fontWeight: 700, color: '#374151', display: 'block', marginBottom: 8 }}>
          {t(lang, 'Actions (execute when matched)', 'Acciones (se ejecutan al coincidir)')}
        </label>
        <ActionEditor actions={actions} onChange={setActions} />
      </div>

      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button style={btn('#F3F4F6', '#6B7280')} onClick={onCancel}>
          {t(lang, 'Cancel', 'Cancelar')}
        </button>
        <button style={{ ...btn(), opacity: saving ? 0.6 : 1 }} onClick={handleSave} disabled={saving || !name.trim()}>
          {saving ? '...' : rule?.id ? t(lang, 'Update', 'Actualizar') : t(lang, 'Create', 'Crear')}
        </button>
      </div>
    </div>
  )
}

// ── Test Panel ────────────────────────────────────────────────────────────────

function TestPanel({ automationId, lang, onClose }) {
  const [inputJson, setInputJson] = useState('{\n  "urgency": "alta",\n  "amount": 15000\n}')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const runTest = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const parsed = JSON.parse(inputJson)
      const res = await fetchAPI('/rules/evaluate', {
        method: 'POST',
        body: JSON.stringify({ automation_id: automationId, input_data: parsed }),
      })
      if (res.error) setError(res.error)
      else setResult(res.data)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  return (
    <div style={{ ...card, border: '2px solid #F59E0B', background: '#FFFBEB' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: '#92400E' }}>
          {t(lang, 'Test Rules', 'Probar reglas')}
        </h4>
        <button style={btnSmall('#FEF3C7', '#92400E')} onClick={onClose}>x</button>
      </div>

      <label style={{ fontSize: 11, fontWeight: 600, color: '#92400E', display: 'block', marginBottom: 4 }}>
        {t(lang, 'Input JSON', 'JSON de entrada')}
      </label>
      <textarea style={{
        ...input, width: '100%', minHeight: 80, fontFamily: 'monospace', fontSize: 12, resize: 'vertical',
        marginBottom: 12, boxSizing: 'border-box',
      }} value={inputJson} onChange={e => setInputJson(e.target.value)} />

      <button style={{ ...btn('#F59E0B', '#fff'), marginBottom: 12, opacity: loading ? 0.6 : 1 }}
        onClick={runTest} disabled={loading}>
        {loading ? '...' : t(lang, 'Evaluate', 'Evaluar')}
      </button>

      {error && <div style={{ padding: 8, borderRadius: 6, background: '#FEE2E2', color: '#DC2626', fontSize: 12, marginBottom: 8 }}>{error}</div>}

      {result && (
        <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #E5E7EB', padding: 12 }}>
          <div style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
            <div>
              <span style={{ fontSize: 11, color: '#9CA3AF' }}>{t(lang, 'Matched rules', 'Reglas coincidentes')}</span>
              <div style={{ fontSize: 20, fontWeight: 700, color: result.total_matched > 0 ? '#10B981' : '#EF4444' }}>
                {result.total_matched}
              </div>
            </div>
            <div>
              <span style={{ fontSize: 11, color: '#9CA3AF' }}>{t(lang, 'Actions to execute', 'Acciones a ejecutar')}</span>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#6366F1' }}>{result.total_actions}</div>
            </div>
          </div>
          {result.matched_rules.map((m, i) => (
            <div key={i} style={{ padding: 8, borderRadius: 6, background: '#F0FDF4', border: '1px solid #BBF7D0', marginBottom: 6 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#166534', marginBottom: 4 }}>{m.name}</div>
              <ActionBadges actions={m.actions} />
            </div>
          ))}
          {result.total_matched === 0 && (
            <div style={{ color: '#9CA3AF', fontSize: 13, textAlign: 'center', padding: 12 }}>
              {t(lang, 'No rules matched the input data.', 'Ninguna regla coincidio con los datos de entrada.')}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function RulesPanel({ automationId, lang = 'en' }) {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null) // null | 'new' | rule object
  const [showTest, setShowTest] = useState(false)
  const [error, setError] = useState(null)

  const loadRules = useCallback(async () => {
    if (!automationId) return
    setLoading(true)
    const res = await fetchAPI(`/rules/automation/${automationId}`)
    if (res.error) setError(res.error)
    else setRules(res.data || [])
    setLoading(false)
  }, [automationId])

  useEffect(() => { loadRules() }, [loadRules])

  const handleToggle = async (rule) => {
    await fetchAPI(`/rules/${rule.id}`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: !rule.is_active }),
    })
    loadRules()
  }

  const handleDelete = async (ruleId) => {
    if (!confirm(t(lang, 'Delete this rule?', 'Eliminar esta regla?'))) return
    await fetchAPI(`/rules/${ruleId}`, { method: 'DELETE' })
    loadRules()
  }

  const handleSave = async (data) => {
    if (editing && editing.id) {
      // Update
      await fetchAPI(`/rules/${editing.id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      })
    } else {
      // Create
      await fetchAPI('/rules/', {
        method: 'POST',
        body: JSON.stringify({ ...data, automation_id: automationId }),
      })
    }
    setEditing(null)
    loadRules()
  }

  if (loading) return (
    <div style={{ padding: 24, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
      {t(lang, 'Loading rules...', 'Cargando reglas...')}
    </div>
  )

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#111827' }}>
            {t(lang, 'Rules Engine', 'Motor de reglas')}
          </h3>
          <p style={{ margin: 0, fontSize: 12, color: '#9CA3AF' }}>
            {t(lang, 'If/Then conditions for this automation', 'Condiciones Si/Entonces para esta automatizacion')}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button style={btn('#F59E0B', '#fff')} onClick={() => setShowTest(!showTest)}>
            {t(lang, 'Test Rules', 'Probar')}
          </button>
          <button style={btn()} onClick={() => setEditing('new')}>
            + {t(lang, 'Add Rule', 'Agregar regla')}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: 8, borderRadius: 6, background: '#FEE2E2', color: '#DC2626', fontSize: 12, marginBottom: 12 }}>{error}</div>
      )}

      {/* Quick templates */}
      {rules.length === 0 && !editing && (
        <div style={{ padding: 14, borderRadius: 10, background: '#F9FAFB', border: '1px dashed #D1D5DB', marginBottom: 12 }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', marginBottom: 8 }}>
            {t(lang, 'Quick templates:', 'Plantillas rapidas:')}
          </p>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {[
              { label: lang === 'es' ? 'Si urgente → notificar' : 'If urgent → notify',
                rule: { name: 'Urgent notification', conditions: [{ field: 'priority', operator: 'equals', value: 'high' }], actions: [{ type: 'notify', config: { message: 'Urgent item detected' } }], priority: 1, is_active: true } },
              { label: lang === 'es' ? 'Si score < 50 → saltar' : 'If score < 50 → skip',
                rule: { name: 'Low quality skip', conditions: [{ field: 'score', operator: 'less_than', value: '50' }], actions: [{ type: 'skip_step', config: { step: 'reporter' } }], priority: 2, is_active: true } },
              { label: lang === 'es' ? 'Si vacio → redirigir' : 'If empty → route',
                rule: { name: 'Empty input redirect', conditions: [{ field: 'text', operator: 'is_empty', value: '' }], actions: [{ type: 'route', config: { agent: 'classifier' } }], priority: 3, is_active: true } },
            ].map((tmpl, i) => (
              <button key={i} onClick={async () => {
                await fetchAPI('/rules/', {
                  method: 'POST',
                  body: JSON.stringify({ automation_id: automationId, ...tmpl.rule }),
                })
                load()
              }} style={{
                padding: '6px 12px', borderRadius: 6, border: '1px solid #E5E7EB',
                background: '#fff', fontSize: 12, cursor: 'pointer', color: '#374151',
              }}>
                {tmpl.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Test panel */}
      {showTest && <TestPanel automationId={automationId} lang={lang} onClose={() => setShowTest(false)} />}

      {/* New rule editor */}
      {editing === 'new' && (
        <RuleEditor lang={lang} onSave={handleSave} onCancel={() => setEditing(null)} />
      )}

      {/* Rules list */}
      {rules.length === 0 && !editing && (
        <div style={{
          ...card, textAlign: 'center', padding: 40, color: '#9CA3AF',
        }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>&#9881;</div>
          <p style={{ fontSize: 14, margin: 0 }}>
            {t(lang, 'No rules yet. Add one to get started.', 'Sin reglas. Agrega una para comenzar.')}
          </p>
        </div>
      )}

      {rules.map(rule => (
        <div key={rule.id} style={{ ...card, opacity: rule.is_active ? 1 : 0.55 }}>
          {editing?.id === rule.id ? (
            <RuleEditor rule={rule} lang={lang} onSave={handleSave} onCancel={() => setEditing(null)} />
          ) : (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                {/* Active toggle */}
                <button onClick={() => handleToggle(rule)} title={rule.is_active ? 'Active' : 'Inactive'}
                  style={{
                    width: 36, height: 20, borderRadius: 10, border: 'none', cursor: 'pointer', position: 'relative',
                    background: rule.is_active ? '#10B981' : '#D1D5DB', transition: 'background 0.2s',
                  }}>
                  <div style={{
                    width: 16, height: 16, borderRadius: '50%', background: '#fff', position: 'absolute', top: 2,
                    left: rule.is_active ? 18 : 2, transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
                  }} />
                </button>

                <div style={{ flex: 1 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{rule.name}</span>
                  {rule.description && (
                    <span style={{ fontSize: 12, color: '#9CA3AF', marginLeft: 8 }}>{rule.description}</span>
                  )}
                </div>

                <span style={{
                  fontSize: 11, fontWeight: 600, color: '#6366F1', background: '#EEF2FF',
                  padding: '2px 8px', borderRadius: 4,
                }}>
                  P{rule.priority}
                </span>

                <button style={btnSmall('#EEF2FF', '#6366F1')} onClick={() => setEditing(rule)}>
                  {t(lang, 'Edit', 'Editar')}
                </button>
                <button style={btnSmall('#FEE2E2', '#DC2626')} onClick={() => handleDelete(rule.id)}>
                  {t(lang, 'Delete', 'Eliminar')}
                </button>
              </div>

              {/* Conditions */}
              <div style={{ marginBottom: 8 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginRight: 8 }}>
                  {t(lang, 'IF', 'SI')}
                </span>
                <ConditionPills conditions={rule.conditions} />
              </div>

              {/* Actions */}
              <div>
                <span style={{ fontSize: 11, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginRight: 8 }}>
                  {t(lang, 'THEN', 'ENTONCES')}
                </span>
                <ActionBadges actions={rule.actions} />
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  )
}
