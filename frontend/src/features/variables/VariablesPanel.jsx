import { useState, useEffect, useCallback } from 'react'
import { fetchAPI } from '../../services/api'
import ConfirmModal from '../../shared/components/ConfirmModal'
import { useConfirm } from '../../shared/hooks/useConfirm'

const MASK = '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022'

const T = {
  en: {
    title: 'Variables',
    key: 'Key',
    value: 'Value',
    secret: 'Secret',
    actions: 'Actions',
    add: '+ Add Variable',
    save: 'Save',
    cancel: 'Cancel',
    empty: 'No variables yet. Add one to get started.',
    keyPlaceholder: 'variable_name',
    valuePlaceholder: 'value',
    confirmDelete: 'Delete this variable?',
    copied: 'Copied!',
  },
  es: {
    title: 'Variables',
    key: 'Clave',
    value: 'Valor',
    secret: 'Secreto',
    actions: 'Acciones',
    add: '+ Agregar Variable',
    save: 'Guardar',
    cancel: 'Cancelar',
    empty: 'Sin variables. Agrega una para comenzar.',
    keyPlaceholder: 'nombre_variable',
    valuePlaceholder: 'valor',
    confirmDelete: 'Eliminar esta variable?',
    copied: 'Copiado!',
  },
}

export default function VariablesPanel({ automationId, lang = 'en' }) {
  const t = T[lang] || T.en
  const [variables, setVariables] = useState([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [editId, setEditId] = useState(null)
  const [form, setForm] = useState({ key: '', value: '', is_secret: false })
  const [revealed, setRevealed] = useState({}) // id -> true if user revealed
  const [copiedId, setCopiedId] = useState(null)
  const [confirmState, showConfirm] = useConfirm()

  const load = useCallback(async () => {
    setLoading(true)
    const res = await fetchAPI(`/variables/automation/${automationId}`)
    if (res.data) setVariables(res.data)
    setLoading(false)
  }, [automationId])

  useEffect(() => { load() }, [load])

  const handleAdd = async () => {
    if (!form.key.trim()) return
    const res = await fetchAPI('/variables/', {
      method: 'POST',
      body: JSON.stringify({ automation_id: automationId, ...form }),
    })
    if (res.data) {
      setAdding(false)
      setForm({ key: '', value: '', is_secret: false })
      load()
    }
  }

  const handleUpdate = async (id) => {
    const res = await fetchAPI(`/variables/${id}`, {
      method: 'PUT',
      body: JSON.stringify(form),
    })
    if (res.data?.updated) {
      setEditId(null)
      setForm({ key: '', value: '', is_secret: false })
      load()
    }
  }

  const handleDelete = async (id) => {
    const ok = await showConfirm(t.confirmDelete)
    if (!ok) return
    await fetchAPI(`/variables/${id}`, { method: 'DELETE' })
    load()
  }

  const handleCopy = (val, id) => {
    navigator.clipboard?.writeText(val)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 1500)
  }

  const startEdit = (v) => {
    setEditId(v.id)
    setForm({ key: v.key, value: v.is_secret ? '' : v.value, is_secret: v.is_secret })
    setAdding(false)
  }

  // ── Styles ──
  const card = {
    background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', overflow: 'hidden',
  }
  const header = {
    padding: '14px 20px', borderBottom: '1px solid #F3F4F6',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  }
  const th = {
    padding: '10px 16px', textAlign: 'left', fontSize: 11,
    fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase',
  }
  const td = { padding: '10px 16px', fontSize: 13, color: '#374151' }
  const btnSmall = (bg, color) => ({
    padding: '4px 10px', borderRadius: 6, border: '1px solid #E5E7EB',
    background: bg || '#fff', fontSize: 11, color: color || '#6B7280',
    cursor: 'pointer', fontWeight: 500,
  })
  const inputStyle = {
    padding: '6px 10px', borderRadius: 6, border: '1px solid #D1D5DB',
    fontSize: 13, outline: 'none', width: '100%',
  }

  return (
    <div style={card}>
      <div style={header}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: 0 }}>
          {t.title}
        </h3>
        <button
          onClick={() => { setAdding(true); setEditId(null); setForm({ key: '', value: '', is_secret: false }) }}
          style={{
            padding: '6px 14px', borderRadius: 8, border: 'none',
            background: '#6366F1', color: '#fff', fontSize: 12,
            fontWeight: 600, cursor: 'pointer',
          }}
        >
          {t.add}
        </button>
      </div>

      {loading ? (
        <div style={{ padding: 32, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>...</div>
      ) : variables.length === 0 && !adding ? (
        <div style={{ padding: 32, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
          {t.empty}
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #E5E7EB' }}>
              <th style={th}>{t.key}</th>
              <th style={th}>{t.value}</th>
              <th style={{ ...th, width: 70, textAlign: 'center' }}>{t.secret}</th>
              <th style={{ ...th, width: 140, textAlign: 'right' }}>{t.actions}</th>
            </tr>
          </thead>
          <tbody>
            {/* Existing rows */}
            {variables.map(v => {
              const isEditing = editId === v.id
              const isRevealed = revealed[v.id]
              const displayVal = v.is_secret ? (isRevealed ? v.value : MASK) : v.value

              if (isEditing) {
                return (
                  <tr key={v.id} style={{ borderBottom: '1px solid #F3F4F6', background: '#F9FAFB' }}>
                    <td style={td}>
                      <input style={inputStyle} value={form.key}
                        onChange={e => setForm(f => ({ ...f, key: e.target.value }))}
                        placeholder={t.keyPlaceholder} />
                    </td>
                    <td style={td}>
                      <input style={inputStyle} value={form.value}
                        type={form.is_secret ? 'password' : 'text'}
                        onChange={e => setForm(f => ({ ...f, value: e.target.value }))}
                        placeholder={t.valuePlaceholder} />
                    </td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      <input type="checkbox" checked={form.is_secret}
                        onChange={e => setForm(f => ({ ...f, is_secret: e.target.checked }))} />
                    </td>
                    <td style={{ ...td, textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                        <button style={btnSmall('#6366F1', '#fff')} onClick={() => handleUpdate(v.id)}>
                          {t.save}
                        </button>
                        <button style={btnSmall()} onClick={() => setEditId(null)}>
                          {t.cancel}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              }

              return (
                <tr key={v.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                  <td style={{ ...td, fontFamily: 'monospace', fontWeight: 500 }}>{v.key}</td>
                  <td style={{ ...td, fontFamily: 'monospace', color: v.is_secret ? '#9CA3AF' : '#374151' }}>
                    {displayVal}
                  </td>
                  <td style={{ ...td, textAlign: 'center' }}>
                    {v.is_secret ? (
                      <button
                        style={{ ...btnSmall(), fontSize: 14, padding: '2px 8px', border: 'none', background: 'none' }}
                        onClick={() => setRevealed(r => ({ ...r, [v.id]: !r[v.id] }))}
                        title={isRevealed ? 'Hide' : 'Show'}
                      >
                        {isRevealed ? '\uD83D\uDC41\uFE0F' : '\uD83D\uDC41\uFE0F\u200D\uD83D\uDDE8\uFE0F'}
                      </button>
                    ) : (
                      <span style={{ color: '#D1D5DB' }}>--</span>
                    )}
                  </td>
                  <td style={{ ...td, textAlign: 'right' }}>
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                      {!v.is_secret && (
                        <button style={btnSmall()} onClick={() => handleCopy(v.value, v.id)}>
                          {copiedId === v.id ? t.copied : 'Copy'}
                        </button>
                      )}
                      <button style={btnSmall()} onClick={() => startEdit(v)}>Edit</button>
                      <button style={btnSmall('#FEE2E2', '#DC2626')} onClick={() => handleDelete(v.id)}>
                        Del
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}

            {/* Add new row */}
            {adding && (
              <tr style={{ borderBottom: '1px solid #F3F4F6', background: '#F0FDF4' }}>
                <td style={td}>
                  <input style={inputStyle} value={form.key}
                    onChange={e => setForm(f => ({ ...f, key: e.target.value }))}
                    placeholder={t.keyPlaceholder} autoFocus />
                </td>
                <td style={td}>
                  <input style={inputStyle} value={form.value}
                    type={form.is_secret ? 'password' : 'text'}
                    onChange={e => setForm(f => ({ ...f, value: e.target.value }))}
                    placeholder={t.valuePlaceholder} />
                </td>
                <td style={{ ...td, textAlign: 'center' }}>
                  <input type="checkbox" checked={form.is_secret}
                    onChange={e => setForm(f => ({ ...f, is_secret: e.target.checked }))} />
                </td>
                <td style={{ ...td, textAlign: 'right' }}>
                  <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                    <button style={btnSmall('#6366F1', '#fff')} onClick={handleAdd}>
                      {t.save}
                    </button>
                    <button style={btnSmall()} onClick={() => setAdding(false)}>
                      {t.cancel}
                    </button>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
      {confirmState && <ConfirmModal {...confirmState} />}
    </div>
  )
}
