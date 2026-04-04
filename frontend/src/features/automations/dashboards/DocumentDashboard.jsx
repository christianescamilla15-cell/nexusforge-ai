import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchAPI, getApiUrl } from '../../../services/api'
import StatsBar from './StatsBar'
import ResultsTable from './ResultsTable'

function formatDate(iso, lang) {
  if (!iso) return '--'
  return new Date(iso).toLocaleString(lang === 'es' ? 'es-ES' : 'en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function formatSize(bytes) {
  if (!bytes) return '--'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

const FILE_ICONS = {
  pdf: '📄', docx: '📝', doc: '📝', txt: '📃',
  png: '🖼️', jpg: '🖼️', jpeg: '🖼️', csv: '📊', xlsx: '📊',
}

function getFileIcon(filename) {
  const ext = (filename || '').split('.').pop().toLowerCase()
  return FILE_ICONS[ext] || '📎'
}

export default function DocumentDashboard({ automation, lang, onBack }) {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [selectedResult, setSelectedResult] = useState(null)
  const [error, setError] = useState(null)
  const [isMobile, setIsMobile] = useState(false)
  const fileInputRef = useRef(null)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const loadResults = useCallback(async () => {
    setLoading(true)
    const res = await fetchAPI(`/results/automation/${automation.id}`)
    if (!res.error && Array.isArray(res.data)) {
      setResults(res.data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)))
    }
    setLoading(false)
  }, [automation.id])

  useEffect(() => { loadResults() }, [loadResults])

  const handleFiles = async (files) => {
    if (!files || files.length === 0 || processing) return
    setProcessing(true)
    setError(null)

    try {
      const file = files[0]

      // Build FormData for upload
      const formData = new FormData()
      formData.append('file', file)
      formData.append('automation_id', automation.id)

      // Try file upload endpoint first
      const apiUrl = getApiUrl()
      const token = localStorage.getItem('nf_token')
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {}

      let runId = null

      try {
        const uploadRes = await fetch(`${apiUrl}/automations/${automation.id}/run`, {
          method: 'POST',
          headers: { ...headers },
          body: formData,
          signal: AbortSignal.timeout(30000),
        })

        if (uploadRes.ok) {
          const data = await uploadRes.json()
          runId = data.run_id
        }
      } catch {
        // Fallback: send file info as JSON
      }

      if (!runId) {
        // Fallback: send file metadata as JSON run
        const runRes = await fetchAPI(`/automations/${automation.id}/run`, {
          method: 'POST',
          body: JSON.stringify({
            input_data: {
              filename: file.name,
              file_type: file.type,
              file_size: file.size,
              content: await readFileAsText(file),
            },
          }),
        })

        if (runRes.error) {
          setError(runRes.error)
          setProcessing(false)
          return
        }
        runId = runRes.data?.run_id
      }

      if (!runId) {
        setError(lang === 'es' ? 'No se obtuvo ID de ejecucion' : 'No run ID returned')
        setProcessing(false)
        return
      }

      // Poll for completion
      let attempts = 0
      const poll = async () => {
        if (attempts > 60) {
          setError(lang === 'es' ? 'Tiempo de espera agotado' : 'Timed out')
          setProcessing(false)
          return
        }
        attempts++
        const execRes = await fetchAPI(`/executions/${runId}`)
        if (execRes.error) {
          setError(execRes.error)
          setProcessing(false)
          return
        }

        const status = execRes.data?.status
        if (status === 'completed') {
          const output = execRes.data?.result || execRes.data?.output || {}
          await fetchAPI('/results/', {
            method: 'POST',
            body: JSON.stringify({
              automation_id: automation.id,
              execution_id: runId,
              input_data: { filename: file.name, file_type: file.type, file_size: file.size },
              output_data: output,
              result_type: 'document',
            }),
          })
          await loadResults()
          setProcessing(false)
        } else if (status === 'failed') {
          setError(execRes.data?.error || (lang === 'es' ? 'La ejecucion fallo' : 'Execution failed'))
          setProcessing(false)
        } else {
          setTimeout(poll, 2000)
        }
      }
      poll()
    } catch (err) {
      setError(err.message)
      setProcessing(false)
    }
  }

  const color = automation.color || '#10B981'
  const totalDocs = results.length
  const totalPages = results.reduce((sum, r) => sum + (r.output_data?.pages || 1), 0)
  const avgTime = results.length > 0
    ? Math.round(results.reduce((sum, r) => sum + (r.output_data?.processing_time_ms || 1200), 0) / results.length)
    : 0

  const totalFieldsExtracted = results.reduce((sum, r) => sum + (r.output_data?.fields?.length || 0), 0)

  const stats = [
    { label: lang === 'es' ? 'Documentos analizados' : 'Documents analyzed', value: totalDocs, color: '#10B981' },
    { label: lang === 'es' ? 'Paginas procesadas' : 'Pages processed', value: totalPages, color: '#6366F1' },
    { label: lang === 'es' ? 'Campos extraidos correctamente' : 'Fields extracted correctly', value: totalFieldsExtracted, color: '#8B5CF6' },
    { label: lang === 'es' ? 'Tiempo promedio' : 'Avg processing time', value: avgTime ? `${(avgTime / 1000).toFixed(1)}s` : '--', color: '#F59E0B' },
  ]

  // Detail view
  if (selectedResult) {
    const out = selectedResult.output_data || {}
    const inp = selectedResult.input_data || {}
    return (
      <div style={{ animation: 'fadeIn 0.2s ease-out' }}>
        <button onClick={() => setSelectedResult(null)} style={{
          background: '#F3F4F6', border: 'none', borderRadius: 8,
          padding: '8px 16px', cursor: 'pointer', fontSize: 13,
          color: '#6B7280', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span>←</span> {lang === 'es' ? 'Volver a resultados' : 'Back to results'}
        </button>

        <div style={{
          background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
          padding: 24, marginBottom: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
            <span style={{ fontSize: 28 }}>{getFileIcon(inp.filename)}</span>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: '#111827', margin: 0 }}>
                {inp.filename || (lang === 'es' ? 'Documento' : 'Document')}
              </h3>
              <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0 }}>
                {inp.file_type} · {formatSize(inp.file_size)} · {formatDate(selectedResult.created_at, lang)}
              </p>
            </div>
          </div>

          {out.summary && (
            <div style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase' }}>
                {lang === 'es' ? 'Resumen' : 'Summary'}
              </p>
              <div style={{
                padding: 12, background: '#F9FAFB', borderRadius: 8,
                border: '1px solid #E5E7EB', fontSize: 13, color: '#374151', lineHeight: 1.6,
              }}>
                {out.summary}
              </div>
            </div>
          )}

          {out.fields && out.fields.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 8, textTransform: 'uppercase' }}>
                {lang === 'es' ? 'Campos extraidos' : 'Extracted fields'}
              </p>
              <div style={{
                background: '#F9FAFB', borderRadius: 8, border: '1px solid #E5E7EB',
                overflow: 'hidden',
              }}>
                {out.fields.map((f, i) => (
                  <div key={i} style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '8px 14px', borderBottom: i < out.fields.length - 1 ? '1px solid #E5E7EB' : 'none',
                    fontSize: 13,
                  }}>
                    <span style={{ color: '#6B7280', fontWeight: 500 }}>{f.name || f.key}</span>
                    <span style={{ color: '#111827' }}>{f.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {out.qa && out.qa.length > 0 && (
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 8, textTransform: 'uppercase' }}>
                Q&A
              </p>
              {out.qa.map((item, i) => (
                <div key={i} style={{ marginBottom: 12 }}>
                  <p style={{ fontSize: 13, fontWeight: 600, color: '#374151', margin: '0 0 4px' }}>
                    Q: {item.question}
                  </p>
                  <p style={{ fontSize: 13, color: '#6B7280', margin: 0, paddingLeft: 12, borderLeft: `2px solid ${color}` }}>
                    {item.answer}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div style={{ animation: 'fadeIn 0.2s ease-out' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <button onClick={onBack} style={{
          background: '#F3F4F6', border: 'none', borderRadius: 8, width: 36, height: 36,
          cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6B7280',
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M19 12H5m7-7l-7 7 7 7" />
          </svg>
        </button>
        <div style={{
          width: 44, height: 44, borderRadius: 12,
          background: `${color}12`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22,
        }}>
          {automation.icon || '📄'}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: '#111827', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {automation.name}
          </h1>
          <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0 }}>
            {lang === 'es' ? 'Analisis inteligente de documentos' : 'Intelligent document analysis'}
          </p>
        </div>
      </div>

      <StatsBar stats={stats} lang={lang} />

      {/* Upload Panel */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
        onClick={() => !processing && fileInputRef.current?.click()}
        style={{
          background: dragOver ? `${color}08` : '#fff',
          borderRadius: 12,
          border: `2px dashed ${dragOver ? color : '#E5E7EB'}`,
          padding: isMobile ? '24px 16px' : '32px 24px',
          marginBottom: 24,
          textAlign: 'center',
          cursor: processing ? 'default' : 'pointer',
          transition: 'all 0.2s',
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg,.csv,.xlsx"
          style={{ display: 'none' }}
          onChange={e => handleFiles(e.target.files)}
        />
        {processing ? (
          <>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" style={{ animation: 'spin 1s linear infinite', margin: '0 auto 12px', display: 'block' }}>
              <path d="M21 12a9 9 0 11-6.219-8.56" />
            </svg>
            <p style={{ fontSize: 14, fontWeight: 600, color: '#374151', margin: '0 0 4px' }}>
              {lang === 'es' ? 'Analizando documento...' : 'Analyzing document...'}
            </p>
          </>
        ) : (
          <>
            <div style={{ fontSize: 32, marginBottom: 8, opacity: 0.6 }}>📁</div>
            <p style={{ fontSize: 14, fontWeight: 600, color: '#374151', margin: '0 0 4px' }}>
              {lang === 'es' ? 'Arrastra un archivo aqui o haz clic para seleccionar' : 'Drag a file here or click to select'}
            </p>
            <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0 }}>
              PDF, DOCX, TXT, PNG, JPG, CSV, XLSX
            </p>
          </>
        )}
        {error && (
          <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 8, background: '#FEF2F2', border: '1px solid #FECACA', fontSize: 12, color: '#DC2626', textAlign: 'left' }}>
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: '0 0 12px' }}>
          {lang === 'es' ? 'Documentos procesados' : 'Processed documents'}
          {results.length > 0 && (
            <span style={{ fontSize: 12, fontWeight: 400, color: '#9CA3AF', marginLeft: 8 }}>
              ({results.length})
            </span>
          )}
        </h3>
      </div>

      {loading ? (
        <div style={{ padding: 32, textAlign: 'center', color: '#9CA3AF' }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ animation: 'spin 1s linear infinite', margin: '0 auto 8px', display: 'block' }}>
            <path d="M21 12a9 9 0 11-6.219-8.56" />
          </svg>
          {lang === 'es' ? 'Cargando...' : 'Loading...'}
        </div>
      ) : results.length === 0 ? (
        <div style={{
          padding: '48px 24px', textAlign: 'center',
          background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
        }}>
          <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.4 }}>📄</div>
          <h4 style={{ fontSize: 15, fontWeight: 600, color: '#374151', margin: '0 0 6px' }}>
            {lang === 'es' ? 'Sin documentos procesados' : 'No documents processed'}
          </h4>
          <p style={{ fontSize: 13, color: '#9CA3AF', margin: 0 }}>
            {lang === 'es'
              ? 'Sube un archivo arriba para comenzar el analisis automatico.'
              : 'Upload a file above to start automatic analysis.'}
          </p>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 12,
        }}>
          {results.map((r) => {
            const inp = r.input_data || {}
            const out = r.output_data || {}
            return (
              <div
                key={r.id}
                onClick={() => setSelectedResult(r)}
                style={{
                  background: '#fff', borderRadius: 10, border: '1px solid #E5E7EB',
                  padding: 16, cursor: 'pointer', transition: 'border-color 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = color}
                onMouseLeave={e => e.currentTarget.style.borderColor = '#E5E7EB'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <span style={{ fontSize: 22 }}>{getFileIcon(inp.filename)}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 13, fontWeight: 600, color: '#111827', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {inp.filename || (lang === 'es' ? 'Documento' : 'Document')}
                    </p>
                    <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>
                      {inp.file_type || '--'} · {formatSize(inp.file_size)}
                    </p>
                  </div>
                </div>
                {out.summary && (
                  <p style={{
                    fontSize: 12, color: '#6B7280', lineHeight: 1.5, margin: '0 0 8px',
                    overflow: 'hidden', display: '-webkit-box',
                    WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                  }}>
                    {out.summary}
                  </p>
                )}
                <div style={{ fontSize: 11, color: '#9CA3AF' }}>
                  {formatDate(r.created_at, lang)}
                  {out.pages && <span> · {out.pages} {lang === 'es' ? 'pags' : 'pages'}</span>}
                </div>
              </div>
            )
          })}
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } } @keyframes fadeIn { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none } }`}</style>
    </div>
  )
}

function readFileAsText(file) {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => resolve('')
    // For images/binary, return base64; for text, return text
    if (file.type.startsWith('image/') || file.type === 'application/pdf') {
      reader.readAsDataURL(file)
    } else {
      reader.readAsText(file)
    }
  })
}
