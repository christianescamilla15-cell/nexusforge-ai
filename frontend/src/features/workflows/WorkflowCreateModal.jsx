import { useState } from 'react'
import Modal from '../../shared/components/Modal'
import { api } from '../../api/client'

const TEMPLATES = [
  {
    name: 'En blanco',
    dag: { steps: [] },
  },
  {
    name: 'Analisis de Documentos',
    dag: {
      steps: [
        { name: 'ingest', type: 'extractor', depends_on: [] },
        { name: 'classify', type: 'classifier', depends_on: ['ingest'] },
        { name: 'summarize', type: 'summarizer', depends_on: ['classify'] },
        { name: 'validate', type: 'validator', depends_on: ['summarize'] },
      ],
    },
  },
  {
    name: 'Clasificacion de Datos',
    dag: {
      steps: [
        { name: 'load_data', type: 'extractor', depends_on: [] },
        { name: 'preprocess', type: 'orchestrator', depends_on: ['load_data'] },
        { name: 'classify_a', type: 'classifier', depends_on: ['preprocess'] },
        { name: 'classify_b', type: 'classifier', depends_on: ['preprocess'] },
        { name: 'merge', type: 'orchestrator', depends_on: ['classify_a', 'classify_b'] },
        { name: 'export', type: 'validator', depends_on: ['merge'] },
      ],
    },
  },
]

const inputStyle = {
  width: '100%', padding: '10px 12px', borderRadius: 8, fontSize: 14,
  border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.03)',
  color: '#E5E7EB', outline: 'none',
}

const labelStyle = {
  display: 'block', fontSize: 13, fontWeight: 500, color: '#9CA3AF', marginBottom: 6,
}

export default function WorkflowCreateModal({ open, onClose, onCreated }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [dagJson, setDagJson] = useState(JSON.stringify(TEMPLATES[0].dag, null, 2))
  const [validationMsg, setValidationMsg] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleTemplate = (templateName) => {
    const tpl = TEMPLATES.find((t) => t.name === templateName)
    if (tpl) {
      setDagJson(JSON.stringify(tpl.dag, null, 2))
      setValidationMsg(null)
    }
  }

  const handleValidate = () => {
    try {
      const parsed = JSON.parse(dagJson)
      if (!parsed.steps || !Array.isArray(parsed.steps)) {
        setValidationMsg({ ok: false, msg: 'El DAG debe tener un array "steps"' })
        return
      }
      const names = parsed.steps.map((s) => s.name)
      const dups = names.filter((n, i) => names.indexOf(n) !== i)
      if (dups.length) {
        setValidationMsg({ ok: false, msg: `Nombres duplicados: ${dups.join(', ')}` })
        return
      }
      for (const step of parsed.steps) {
        for (const dep of step.depends_on || []) {
          if (!names.includes(dep)) {
            setValidationMsg({ ok: false, msg: `Dependencia "${dep}" no existe en paso "${step.name}"` })
            return
          }
        }
      }
      setValidationMsg({ ok: true, msg: `DAG valido: ${parsed.steps.length} pasos` })
    } catch (e) {
      setValidationMsg({ ok: false, msg: `JSON invalido: ${e.message}` })
    }
  }

  const handleSave = async () => {
    if (!name.trim()) { setError('El nombre es requerido'); return }
    handleValidate()
    try {
      JSON.parse(dagJson)
    } catch {
      return
    }

    setSaving(true)
    setError(null)
    try {
      await api.post('/workflows', {
        name: name.trim(),
        description: description.trim(),
        dag_definition: JSON.parse(dagJson),
      })
      setName('')
      setDescription('')
      setDagJson(JSON.stringify(TEMPLATES[0].dag, null, 2))
      setValidationMsg(null)
      onCreated()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Nuevo Workflow" width={640}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div>
          <label style={labelStyle}>Nombre</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ej: Pipeline de Analisis"
            aria-label="Nombre del workflow"
            style={inputStyle}
            onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
            onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
          />
        </div>

        <div>
          <label style={labelStyle}>Descripcion</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe el proposito del workflow..."
            aria-label="Descripcion del workflow"
            rows={3}
            style={{ ...inputStyle, resize: 'vertical' }}
            onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
            onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
          />
        </div>

        <div>
          <label style={labelStyle}>Plantilla</label>
          <select
            onChange={(e) => handleTemplate(e.target.value)}
            aria-label="Seleccionar plantilla"
            style={{ ...inputStyle, cursor: 'pointer' }}
          >
            {TEMPLATES.map((t) => (
              <option key={t.name} value={t.name} style={{ background: '#161E2E' }}>
                {t.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <label style={{ ...labelStyle, marginBottom: 0 }}>Definicion DAG (JSON)</label>
            <button
              onClick={handleValidate}
              aria-label="Validar DAG"
              style={{
                padding: '4px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                border: '1px solid rgba(99,102,241,0.3)', background: 'transparent',
                color: '#818CF8', cursor: 'pointer',
              }}
            >
              Validar
            </button>
          </div>
          <textarea
            value={dagJson}
            onChange={(e) => { setDagJson(e.target.value); setValidationMsg(null) }}
            aria-label="Definicion DAG en formato JSON"
            rows={10}
            style={{
              ...inputStyle,
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              fontSize: 13,
              lineHeight: 1.5,
              resize: 'vertical',
            }}
            onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
            onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
          />
          {validationMsg && (
            <div style={{
              marginTop: 8, padding: '8px 12px', borderRadius: 6, fontSize: 12,
              background: validationMsg.ok ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
              color: validationMsg.ok ? '#10B981' : '#EF4444',
              border: `1px solid ${validationMsg.ok ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
            }}>
              {validationMsg.msg}
            </div>
          )}
        </div>

        {error && (
          <div style={{
            padding: '8px 12px', borderRadius: 6, fontSize: 13,
            background: 'rgba(239,68,68,0.1)', color: '#EF4444',
            border: '1px solid rgba(239,68,68,0.2)',
          }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 }}>
          <button
            onClick={onClose}
            aria-label="Cancelar"
            style={{
              padding: '10px 20px', borderRadius: 8, fontSize: 14,
              border: '1px solid rgba(255,255,255,0.1)', background: 'transparent',
              color: '#9CA3AF', cursor: 'pointer',
            }}
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            aria-label="Guardar workflow"
            style={{
              padding: '10px 20px', borderRadius: 8, fontSize: 14, fontWeight: 500,
              border: 'none', background: '#6366F1', color: '#fff', cursor: 'pointer',
              opacity: saving ? 0.6 : 1, transition: 'opacity 0.2s',
            }}
          >
            {saving ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
