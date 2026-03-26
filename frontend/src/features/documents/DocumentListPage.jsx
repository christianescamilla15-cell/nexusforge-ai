import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import StatusBadge from '../../shared/components/StatusBadge'
import DocumentUpload from './DocumentUpload'
import SemanticSearch from './SemanticSearch'

const DOC_STATUS = {
  uploaded: { bg: 'rgba(96,165,250,0.15)', color: '#60A5FA', label: 'Subido' },
  processing: { bg: 'rgba(245,158,11,0.15)', color: '#F59E0B', label: 'Procesando' },
  indexed: { bg: 'rgba(16,185,129,0.15)', color: '#10B981', label: 'Indexado' },
  failed: { bg: 'rgba(239,68,68,0.15)', color: '#EF4444', label: 'Fallido' },
}

const DEMO_DOCS = [
  { id: 'doc-1', title: 'Contrato de Servicios 2026', file_type: 'pdf', language: 'es', status: 'indexed', size_kb: 245, created_at: '2026-03-20T10:00:00Z' },
  { id: 'doc-2', title: 'Politica de Privacidad v3', file_type: 'text', language: 'es', status: 'indexed', size_kb: 82, created_at: '2026-03-18T14:30:00Z' },
  { id: 'doc-3', title: 'Reporte Financiero Q1', file_type: 'csv', language: 'es', status: 'indexed', size_kb: 1200, created_at: '2026-03-22T09:15:00Z' },
  { id: 'doc-4', title: 'API Documentation v2', file_type: 'text', language: 'en', status: 'indexed', size_kb: 156, created_at: '2026-03-15T16:45:00Z' },
  { id: 'doc-5', title: 'Meeting Notes March', file_type: 'text', language: 'en', status: 'processing', size_kb: 34, created_at: '2026-03-26T08:00:00Z' },
  { id: 'doc-6', title: 'Error Log Analysis', file_type: 'csv', language: 'en', status: 'failed', size_kb: 890, created_at: '2026-03-25T11:20:00Z' },
]

function DocStatusBadge({ status }) {
  const s = DOC_STATUS[status] || DOC_STATUS.uploaded
  return (
    <span aria-label={`Estado: ${s.label}`} style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '3px 10px', borderRadius: 9999, fontSize: 12, fontWeight: 500,
      background: s.bg, color: s.color, whiteSpace: 'nowrap',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.color, flexShrink: 0 }} />
      {s.label}
    </span>
  )
}

function formatDate(iso) {
  if (!iso) return '--'
  return new Date(iso).toLocaleDateString('es-ES', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatSize(kb) {
  if (!kb) return '--'
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)} MB`
  return `${kb} KB`
}

export default function DocumentListPage() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)

  const fetchDocs = async () => {
    try {
      const data = await api.get('/documents')
      setDocs(Array.isArray(data) ? data : data.items || DEMO_DOCS)
    } catch {
      setDocs(DEMO_DOCS)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchDocs() }, [])

  if (loading) {
    return (
      <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 8 }}>Documentos</h1>
        <p style={{ fontSize: 14, color: '#9CA3AF' }}>Cargando documentos...</p>
      </div>
    )
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 4 }}>Documentos</h1>
          <p style={{ fontSize: 14, color: '#9CA3AF' }}>
            Administra los documentos indexados en el sistema.
            <span style={{ marginLeft: 8, color: '#6366F1' }}>{docs.length} documentos</span>
          </p>
        </div>
        <button
          onClick={() => setShowUpload(!showUpload)}
          aria-label="Subir documento"
          style={{
            padding: '10px 20px', borderRadius: 8, border: 'none',
            background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
            color: '#fff', fontSize: 14, fontWeight: 600,
            cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Subir
        </button>
      </div>

      {/* Upload form */}
      {showUpload && (
        <DocumentUpload
          onClose={() => setShowUpload(false)}
          onUploaded={fetchDocs}
        />
      )}

      {/* Semantic Search */}
      <SemanticSearch />

      {/* Table */}
      <div style={{
        background: '#161E2E', borderRadius: 12,
        border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden',
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              {['Titulo', 'Tipo', 'Idioma', 'Estado', 'Tamano', 'Creado'].map((h) => (
                <th key={h} style={{
                  padding: '12px 16px', fontSize: 12, fontWeight: 600, color: '#9CA3AF',
                  textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.05em',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {docs.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
                  No hay documentos. Sube uno para comenzar.
                </td>
              </tr>
            )}
            {docs.map((doc) => (
              <tr key={doc.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <td style={{ padding: '12px 16px', color: '#E5E7EB', fontSize: 14, fontWeight: 500 }}>{doc.title}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{
                    fontSize: 11, padding: '2px 8px', borderRadius: 4,
                    background: 'rgba(99,102,241,0.1)', color: '#A5B4FC', fontWeight: 500,
                    textTransform: 'uppercase',
                  }}>{doc.file_type}</span>
                </td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13, textTransform: 'uppercase' }}>{doc.language}</td>
                <td style={{ padding: '12px 16px' }}><DocStatusBadge status={doc.status} /></td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13 }}>{formatSize(doc.size_kb)}</td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13 }}>{formatDate(doc.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
