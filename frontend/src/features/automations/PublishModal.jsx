import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

const ICONS = ['⚡', '📊', '🔄', '📧', '📄', '🤖', '🔍', '💰', '🏢', '🐝', '🧠', '🔗']
const COLORS = ['#6366F1', '#10B981', '#F59E0B', '#EC4899', '#3B82F6', '#8B5CF6', '#EF4444', '#0891B2']

export default function PublishModal({ onClose, onPublished, lang = 'en' }) {
  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState({ name: '', description: '', icon: '⚡', color: '#6366F1', trigger_type: 'manual', schedule_cron: '' })
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
      }),
    })
    setSaving(false)
    if (res.error) { setError(res.error); return }
    onPublished && onPublished()
    onClose()
  }

  const inputStyle = {
    width: '100%', padding: '8px 12px', borderRadius: 8,
    border: '1px solid #E5E7EB', fontSize: 13, color: '#111827',
    background: '#fff', boxSizing: 'border-box', outline: 'none',
  }

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 100, backdropFilter: 'blur(4px)',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#fff', borderRadius: 16, padding: 28,
        width: '90%', maxWidth: 600, maxHeight: '88vh', overflowY: 'auto',
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
          /* Step 2: configure */
          <>
            <div style={{ padding: '8px 12px', borderRadius: 8, background: '#EEF2FF', marginBottom: 20, fontSize: 13, color: '#4338CA' }}>
              {lang === 'es' ? 'Workflow:' : 'Workflow:'} <strong>{selected.name}</strong>
              <button onClick={() => setSelected(null)} style={{ marginLeft: 8, background: 'none', border: 'none', color: '#6366F1', cursor: 'pointer', fontSize: 12 }}>
                {lang === 'es' ? 'cambiar' : 'change'}
              </button>
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
                {lang === 'es' ? 'Nombre' : 'Name'}
              </label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} style={inputStyle} />
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
                {lang === 'es' ? 'Descripción' : 'Description'}
              </label>
              <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                rows={2} style={{ ...inputStyle, resize: 'vertical' }} />
            </div>

            {/* Icon picker */}
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
                {lang === 'es' ? 'Ícono' : 'Icon'}
              </label>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {ICONS.map(ic => (
                  <button key={ic} onClick={() => setForm(f => ({ ...f, icon: ic }))} style={{
                    width: 36, height: 36, borderRadius: 8, border: `2px solid ${form.icon === ic ? '#6366F1' : '#E5E7EB'}`,
                    background: form.icon === ic ? '#EEF2FF' : '#F9FAFB', fontSize: 18, cursor: 'pointer',
                  }}>{ic}</button>
                ))}
              </div>
            </div>

            {/* Color picker */}
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
                {lang === 'es' ? 'Color' : 'Color'}
              </label>
              <div style={{ display: 'flex', gap: 6 }}>
                {COLORS.map(c => (
                  <button key={c} onClick={() => setForm(f => ({ ...f, color: c }))} style={{
                    width: 28, height: 28, borderRadius: '50%', background: c, border: `3px solid ${form.color === c ? '#111827' : 'transparent'}`,
                    cursor: 'pointer',
                  }} />
                ))}
              </div>
            </div>

            {/* Trigger type */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
                {lang === 'es' ? 'Tipo de disparo' : 'Trigger type'}
              </label>
              <div style={{ display: 'flex', gap: 8 }}>
                {['manual', 'schedule', 'webhook'].map(t => (
                  <button key={t} onClick={() => setForm(f => ({ ...f, trigger_type: t }))} style={{
                    padding: '6px 14px', borderRadius: 8, border: `1px solid ${form.trigger_type === t ? '#6366F1' : '#E5E7EB'}`,
                    background: form.trigger_type === t ? '#EEF2FF' : '#F9FAFB',
                    color: form.trigger_type === t ? '#6366F1' : '#6B7280',
                    fontSize: 12, fontWeight: 600, cursor: 'pointer', textTransform: 'capitalize',
                  }}>{t}</button>
                ))}
              </div>
              {form.trigger_type === 'schedule' && (
                <input value={form.schedule_cron} onChange={e => setForm(f => ({ ...f, schedule_cron: e.target.value }))}
                  placeholder="0 9 * * 1-5" style={{ ...inputStyle, marginTop: 8 }} />
              )}
              {form.trigger_type === 'webhook' && (
                <p style={{ fontSize: 11, color: '#9CA3AF', marginTop: 6 }}>
                  {lang === 'es' ? 'Se generará una URL de webhook al publicar.' : 'A webhook URL will be generated on publish.'}
                </p>
              )}
            </div>

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
