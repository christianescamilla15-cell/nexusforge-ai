import { useState, useEffect } from 'react'
import { t } from '../../shared/i18n/translations'
import StatusBadge from '../../shared/components/StatusBadge'
import DocumentUpload from './DocumentUpload'
import SemanticSearch from './SemanticSearch'

const DOC_STATUS = {
  uploaded: { bg: 'rgba(96,165,250,0.15)', color: '#60A5FA', label_en: 'Uploaded', label_es: 'Subido' },
  processing: { bg: 'rgba(245,158,11,0.15)', color: '#F59E0B', label_en: 'Processing', label_es: 'Procesando' },
  indexed: { bg: 'rgba(16,185,129,0.15)', color: '#10B981', label_en: 'Indexed', label_es: 'Indexado' },
  failed: { bg: 'rgba(239,68,68,0.15)', color: '#EF4444', label_en: 'Failed', label_es: 'Fallido' },
}

const DEMO_DOCS = [
  { id: 'doc-1', title: 'Contrato de Servicios 2026', file_type: 'pdf', language: 'es', status: 'indexed', size_kb: 245, created_at: '2026-03-20T10:00:00Z' },
  { id: 'doc-2', title: 'Politica de Privacidad v3', file_type: 'text', language: 'es', status: 'indexed', size_kb: 82, created_at: '2026-03-18T14:30:00Z' },
  { id: 'doc-3', title: 'Reporte Financiero Q1', file_type: 'csv', language: 'es', status: 'indexed', size_kb: 1200, created_at: '2026-03-22T09:15:00Z' },
  { id: 'doc-4', title: 'API Documentation v2', file_type: 'text', language: 'en', status: 'indexed', size_kb: 156, created_at: '2026-03-15T16:45:00Z' },
  { id: 'doc-5', title: 'Meeting Notes March', file_type: 'text', language: 'en', status: 'processing', size_kb: 34, created_at: '2026-03-26T08:00:00Z' },
  { id: 'doc-6', title: 'Error Log Analysis', file_type: 'csv', language: 'en', status: 'failed', size_kb: 890, created_at: '2026-03-25T11:20:00Z' },
]

function DocStatusBadge({ status, lang }) {
  const s = DOC_STATUS[status] || DOC_STATUS.uploaded
  const label = lang === 'es' ? s.label_es : s.label_en
  return (
    <span aria-label={`${t('status', lang)}: ${label}`} style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '3px 10px', borderRadius: 9999, fontSize: 12, fontWeight: 500,
      background: s.bg, color: s.color, whiteSpace: 'nowrap',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.color, flexShrink: 0 }} />
      {label}
    </span>
  )
}

function formatDate(iso, lang) {
  if (!iso) return '--'
  const locale = lang === 'es' ? 'es-ES' : 'en-US'
  return new Date(iso).toLocaleDateString(locale, { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatSize(kb) {
  if (!kb) return '--'
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)} MB`
  return `${kb} KB`
}

export default function DocumentListPage({ lang = 'en' }) {
  // Always start with demo data — no backend required
  const [docs] = useState(DEMO_DOCS)
  const [showUpload, setShowUpload] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const tableHeaders = [t('title', lang), t('type', lang), t('lang', lang), t('status', lang), t('size', lang), t('created', lang)]

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 24, flexWrap: 'wrap', gap: 12,
      }}>
        <div>
          <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 4 }}>
            {t('documents', lang)}
          </h1>
          <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
            {t('manageDocuments', lang)}
            <span style={{ marginLeft: 8, color: '#6366F1' }}>{docs.length} {t('documentsCount', lang)}</span>
          </p>
        </div>
        <button
          onClick={() => setShowUpload(!showUpload)}
          aria-label={t('uploadDocument', lang)}
          style={{
            padding: '10px 20px', borderRadius: 8, border: 'none',
            background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
            color: '#fff', fontSize: 14, fontWeight: 600,
            cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
            width: isMobile ? '100%' : 'auto',
            justifyContent: 'center',
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          {t('upload', lang)}
        </button>
      </div>

      {/* Upload form */}
      {showUpload && (
        <DocumentUpload
          onClose={() => setShowUpload(false)}
          onUploaded={() => {}}
        />
      )}

      {/* Semantic Search */}
      <SemanticSearch />

      {/* Table */}
      <div style={{
        background: '#161E2E', borderRadius: 12,
        border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden',
        overflowX: 'auto',
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: isMobile ? 600 : undefined }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              {tableHeaders.map((h) => (
                <th key={h} style={{
                  padding: '12px 16px', fontSize: 12, fontWeight: 600, color: '#9CA3AF',
                  textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.05em',
                  whiteSpace: 'nowrap',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {docs.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
                  {t('noDocuments', lang)}
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
                <td style={{ padding: '12px 16px' }}><DocStatusBadge status={doc.status} lang={lang} /></td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13 }}>{formatSize(doc.size_kb)}</td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13, whiteSpace: 'nowrap' }}>{formatDate(doc.created_at, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
