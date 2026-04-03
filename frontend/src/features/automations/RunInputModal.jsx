import { useState } from 'react'

export default function RunInputModal({ automation, onSubmit, onClose, lang = 'en' }) {
  const config = automation.input_config || { type: 'none' }
  const [text, setText] = useState('')
  const [jsonText, setJsonText] = useState('{}')
  const [formValues, setFormValues] = useState({})
  const [jsonError, setJsonError] = useState(null)

  const inputStyle = {
    width: '100%', padding: '9px 12px', borderRadius: 8,
    border: '1px solid #E5E7EB', fontSize: 13, color: '#111827',
    background: '#fff', boxSizing: 'border-box', outline: 'none',
  }

  const handleSubmit = () => {
    let input_data = {}
    if (config.type === 'text') {
      input_data = { text }
    } else if (config.type === 'json') {
      try {
        input_data = JSON.parse(jsonText)
        setJsonError(null)
      } catch {
        setJsonError(lang === 'es' ? 'JSON inválido' : 'Invalid JSON')
        return
      }
    } else if (config.type === 'form') {
      input_data = { ...formValues }
    }
    onSubmit(input_data)
  }

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 110, backdropFilter: 'blur(4px)',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#fff', borderRadius: 16, padding: 28,
        width: '90%', maxWidth: 520,
        border: '1px solid #E5E7EB', boxShadow: '0 24px 48px rgba(0,0,0,0.2)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 22 }}>{automation.icon}</span>
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: '#111827', margin: 0 }}>{automation.name}</h2>
              <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0 }}>
                {lang === 'es' ? 'Ingresa los datos para ejecutar' : 'Enter data to run'}
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: '#F3F4F6', border: 'none', borderRadius: 8, width: 32, height: 32, cursor: 'pointer', fontSize: 16, color: '#6B7280' }}>✕</button>
        </div>

        {/* Text input */}
        {config.type === 'text' && (
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 8 }}>
              {config.label || (lang === 'es' ? 'Texto a procesar' : 'Text to process')}
            </label>
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              placeholder={config.placeholder || (lang === 'es' ? 'Escribe o pega tu texto aquí...' : 'Type or paste your text here...')}
              rows={6}
              style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.5 }}
              autoFocus
            />
          </div>
        )}

        {/* JSON input */}
        {config.type === 'json' && (
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 8 }}>
              {config.label || 'JSON'}
            </label>
            <textarea
              value={jsonText}
              onChange={e => { setJsonText(e.target.value); setJsonError(null) }}
              rows={8}
              style={{ ...inputStyle, fontFamily: 'monospace', fontSize: 12, resize: 'vertical' }}
              autoFocus
            />
            {jsonError && <p style={{ fontSize: 12, color: '#EF4444', marginTop: 4 }}>{jsonError}</p>}
          </div>
        )}

        {/* Dynamic form */}
        {config.type === 'form' && config.fields?.map(field => (
          <div key={field.key} style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
              {field.label}
            </label>
            {field.type === 'select' ? (
              <select
                value={formValues[field.key] || ''}
                onChange={e => setFormValues(v => ({ ...v, [field.key]: e.target.value }))}
                style={inputStyle}
              >
                <option value="">{lang === 'es' ? 'Seleccionar...' : 'Select...'}</option>
                {(field.options || []).map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            ) : field.type === 'textarea' ? (
              <textarea
                value={formValues[field.key] || ''}
                onChange={e => setFormValues(v => ({ ...v, [field.key]: e.target.value }))}
                placeholder={field.placeholder || ''}
                rows={4}
                style={{ ...inputStyle, resize: 'vertical' }}
              />
            ) : (
              <input
                type={field.type || 'text'}
                value={formValues[field.key] || ''}
                onChange={e => setFormValues(v => ({ ...v, [field.key]: e.target.value }))}
                placeholder={field.placeholder || ''}
                style={inputStyle}
              />
            )}
          </div>
        ))}

        <button
          onClick={handleSubmit}
          style={{
            width: '100%', padding: '11px 0', borderRadius: 9, border: 'none',
            background: `linear-gradient(135deg, ${automation.color || '#6366F1'}, ${automation.color || '#8B5CF6'})`,
            color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}
        >
          <span>▶</span>
          {lang === 'es' ? 'Ejecutar' : 'Run'}
        </button>
      </div>
    </div>
  )
}
