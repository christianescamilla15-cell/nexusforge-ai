import { useState } from 'react'
import { api } from '../../api/client'

export default function DocumentUpload({ onClose, onUploaded }) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [fileType, setFileType] = useState('text')
  const [language, setLanguage] = useState('es')
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!title.trim() || !content.trim()) return
    setUploading(true)
    setError(null)
    try {
      await api.post('/documents', { title, content, file_type: fileType, language })
      setSuccess(true)
      setTimeout(() => {
        onUploaded?.()
        onClose?.()
      }, 1500)
    } catch (err) {
      setError(err.message || 'Error al subir documento')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{
      background: '#FFFFFF', borderRadius: 12,
      border: '1px solid #E5E7EB',
      padding: 24, marginBottom: 24, animation: 'fadeIn 0.2s ease-out',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, color: '#111827', margin: 0 }}>Subir Documento</h2>
        <button onClick={onClose} aria-label="Cerrar formulario" style={{
          background: '#F3F4F6', border: 'none', borderRadius: 8,
          width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', color: '#9CA3AF',
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
        </button>
      </div>

      {success && (
        <div style={{
          padding: '12px 16px', borderRadius: 8, marginBottom: 16,
          background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)',
          color: '#10B981', fontSize: 14,
        }}>
          Documento subido exitosamente.
        </div>
      )}

      {error && (
        <div style={{
          padding: '12px 16px', borderRadius: 8, marginBottom: 16,
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)',
          color: '#EF4444', fontSize: 14,
        }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Title */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Título</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Nombre del documento..."
            aria-label="Título del documento"
            required
            style={inputStyle}
            onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
            onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
          />
        </div>

        {/* Content */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={labelStyle}>Contenido</label>
            <span style={{ fontSize: 11, color: '#9CA3AF' }}>{content.length} caracteres</span>
          </div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Pega el contenido del documento aquí..."
            aria-label="Contenido del documento"
            required
            rows={10}
            style={{ ...inputStyle, minHeight: 200, resize: 'vertical', fontFamily: 'inherit' }}
            onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
            onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
          />
        </div>

        {/* Selectors row */}
        <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 140 }}>
            <label style={labelStyle}>Tipo de archivo</label>
            <select value={fileType} onChange={(e) => setFileType(e.target.value)} aria-label="Tipo de archivo" style={inputStyle}>
              <option value="text">Texto</option>
              <option value="pdf">PDF</option>
              <option value="csv">CSV</option>
            </select>
          </div>
          <div style={{ flex: 1, minWidth: 140 }}>
            <label style={labelStyle}>Idioma</label>
            <select value={language} onChange={(e) => setLanguage(e.target.value)} aria-label="Idioma del documento" style={inputStyle}>
              <option value="es">Español</option>
              <option value="en">English</option>
            </select>
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={uploading || !title.trim() || !content.trim()}
          aria-label="Subir documento"
          style={{
            padding: '10px 24px', borderRadius: 8, border: 'none',
            background: uploading ? 'rgba(99,102,241,0.3)' : 'linear-gradient(135deg, #2563EB, #3B82F6)',
            color: '#fff', fontSize: 14, fontWeight: 600,
            cursor: uploading ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s', width: '100%',
          }}
        >
          {uploading ? 'Subiendo...' : 'Subir Documento'}
        </button>
      </form>
    </div>
  )
}

const labelStyle = {
  display: 'block', fontSize: 12, fontWeight: 600, color: '#9CA3AF',
  textTransform: 'uppercase', marginBottom: 6,
}

const inputStyle = {
  width: '100%', padding: '10px 14px', borderRadius: 8,
  border: '1px solid #E5E7EB', background: '#F3F4F6',
  color: '#111827', fontSize: 14, outline: 'none', boxSizing: 'border-box',
}
