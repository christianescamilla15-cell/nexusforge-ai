import { useState, useEffect, useRef } from 'react'
import { fetchAPI, api } from '../../services/api'
import { t } from '../../shared/i18n/translations'

const TABS = ['upload', 'drive', 'history']

export default function AnalyzePage({ lang = 'es' }) {
  const [tab, setTab] = useState('upload')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Upload state
  const [file, setFile] = useState(null)
  const [textInput, setTextInput] = useState('')
  const [questions, setQuestions] = useState('')
  const [language, setLanguage] = useState(lang)
  const [sendEmail, setSendEmail] = useState(true)
  const [saveNotion, setSaveNotion] = useState(true)
  const fileRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)

  // Drive state
  const [driveFiles, setDriveFiles] = useState([])
  const [driveLoading, setDriveLoading] = useState(false)
  const [driveSearch, setDriveSearch] = useState('')

  // History state
  const [runs, setRuns] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  const bg = isDark ? '#1A1D23' : '#FFFFFF'
  const bgCard = isDark ? '#22252B' : '#F9FAFB'
  const border = isDark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'
  const textPrimary = isDark ? '#F3F4F6' : '#111827'
  const textSecondary = isDark ? '#9CA3AF' : '#6B7280'
  const accent = '#2563EB'
  const green = '#10B981'
  const red = '#EF4444'

  // Load drive files when tab changes
  useEffect(() => {
    if (tab === 'drive') loadDriveFiles()
    if (tab === 'history') loadHistory()
  }, [tab])

  async function loadDriveFiles() {
    setDriveLoading(true)
    try {
      const res = await fetchAPI('/workflows/drive-to-intelligence/files')
      if (res.data?.files) setDriveFiles(res.data.files)
    } catch (e) {
      setDriveFiles([])
    }
    setDriveLoading(false)
  }

  async function loadHistory() {
    setHistoryLoading(true)
    try {
      const res = await fetchAPI('/pipeline-runs?limit=20')
      if (res.data?.runs) setRuns(res.data.runs)
    } catch (e) {
      setRuns([])
    }
    setHistoryLoading(false)
  }

  async function handleUpload() {
    if (!file && !textInput.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      if (file) {
        formData.append('file', file)
      }
      formData.append('language', language)
      formData.append('send_email', sendEmail)
      formData.append('save_to_notion', saveNotion)
      if (questions.trim()) formData.append('questions', questions)

      const apiUrl = localStorage.getItem('nexusforge_api_url') ||
        import.meta.env.VITE_API_URL ||
        'https://nexusforge-api.onrender.com/api'

      const endpoint = file ? '/analyze' : '/analyze/text'
      if (!file) formData.append('content', textInput)

      const resp = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        body: formData,
      })
      const data = await resp.json()
      setResult(data)
      if (data.status === 'error') setError(data.message || 'Analysis failed')
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  async function handleDriveProcess(fileId, fileName) {
    setLoading(true)
    setError(null)
    setResult(null)
    setTab('upload') // Switch to see results

    try {
      const apiUrl = localStorage.getItem('nexusforge_api_url') ||
        import.meta.env.VITE_API_URL ||
        'https://nexusforge-api.onrender.com/api'

      const resp = await fetch(`${apiUrl}/workflows/drive-to-intelligence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_id: fileId,
          language,
          save_to_notion: saveNotion,
          send_webhook: false,
          send_email: sendEmail,
          send_whatsapp: false,
        }),
      })
      const data = await resp.json()
      setResult(data)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  const tabLabels = {
    upload: lang === 'es' ? 'Subir Archivo' : 'Upload File',
    drive: lang === 'es' ? 'Google Drive' : 'Google Drive',
    history: lang === 'es' ? 'Historial' : 'History',
  }

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      {/* Header */}
      <h1 style={{ fontSize: 28, fontWeight: 700, color: textPrimary, margin: 0 }}>
        AI Analyze
      </h1>
      <p style={{ color: textSecondary, margin: '4px 0 24px', fontSize: 15 }}>
        {lang === 'es'
          ? 'Sube archivos o selecciona de Drive. IA analiza, genera preguntas, envia a Gmail y Notion.'
          : 'Upload files or pick from Drive. AI analyzes, generates Q&A, sends to Gmail and Notion.'}
      </p>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, borderBottom: `2px solid ${border}`, marginBottom: 24 }}>
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '10px 20px',
              fontSize: 14,
              fontWeight: tab === t ? 600 : 400,
              color: tab === t ? accent : textSecondary,
              background: 'transparent',
              border: 'none',
              borderBottom: tab === t ? `2px solid ${accent}` : '2px solid transparent',
              cursor: 'pointer',
              marginBottom: -2,
            }}
          >
            {tabLabels[t]}
          </button>
        ))}
      </div>

      {/* TAB: Upload */}
      {tab === 'upload' && (
        <div>
          {/* Drop zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            style={{
              border: `2px dashed ${dragOver ? accent : border}`,
              borderRadius: 12,
              padding: 40,
              textAlign: 'center',
              cursor: 'pointer',
              background: dragOver ? (isDark ? '#1E293B' : '#EFF6FF') : bgCard,
              transition: 'all 0.2s',
              marginBottom: 16,
            }}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt,.csv,.md"
              style={{ display: 'none' }}
              onChange={(e) => setFile(e.target.files[0])}
            />
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke={accent} strokeWidth="1.5" style={{ margin: '0 auto 12px' }}>
              <path d="M12 16V4m0 0l-4 4m4-4l4 4M4 20h16" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {file ? (
              <p style={{ color: textPrimary, fontWeight: 600, fontSize: 16 }}>
                {file.name} ({(file.size / 1024).toFixed(0)} KB)
              </p>
            ) : (
              <>
                <p style={{ color: textPrimary, fontWeight: 600, fontSize: 16, margin: 0 }}>
                  {lang === 'es' ? 'Arrastra un archivo o haz clic' : 'Drag a file or click to browse'}
                </p>
                <p style={{ color: textSecondary, fontSize: 13, margin: '4px 0 0' }}>
                  PDF, Word (.docx), TXT, CSV, Markdown
                </p>
              </>
            )}
          </div>

          {/* Or text input */}
          <details style={{ marginBottom: 16 }}>
            <summary style={{ color: textSecondary, cursor: 'pointer', fontSize: 14 }}>
              {lang === 'es' ? 'O pega texto directo...' : 'Or paste text directly...'}
            </summary>
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder={lang === 'es' ? 'Pega el texto del documento aqui...' : 'Paste document text here...'}
              rows={5}
              style={{
                width: '100%',
                padding: 12,
                borderRadius: 8,
                border: `1px solid ${border}`,
                background: bgCard,
                color: textPrimary,
                fontSize: 14,
                resize: 'vertical',
                marginTop: 8,
                boxSizing: 'border-box',
              }}
            />
          </details>

          {/* Options */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 16, alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, color: textSecondary }}>
              <input type="checkbox" checked={sendEmail} onChange={(e) => setSendEmail(e.target.checked)} />
              {lang === 'es' ? 'Enviar a Gmail' : 'Send to Gmail'}
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, color: textSecondary }}>
              <input type="checkbox" checked={saveNotion} onChange={(e) => setSaveNotion(e.target.checked)} />
              {lang === 'es' ? 'Guardar en Notion' : 'Save to Notion'}
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              style={{ padding: '6px 10px', borderRadius: 6, border: `1px solid ${border}`, background: bgCard, color: textPrimary, fontSize: 13 }}
            >
              <option value="es">Espanol</option>
              <option value="en">English</option>
            </select>
          </div>

          {/* Custom questions */}
          <input
            value={questions}
            onChange={(e) => setQuestions(e.target.value)}
            placeholder={lang === 'es' ? 'Preguntas personalizadas (separadas por coma) — o deja vacio para auto-generar' : 'Custom questions (comma-separated) — leave empty for auto-generation'}
            style={{
              width: '100%',
              padding: 10,
              borderRadius: 8,
              border: `1px solid ${border}`,
              background: bgCard,
              color: textPrimary,
              fontSize: 14,
              marginBottom: 16,
              boxSizing: 'border-box',
            }}
          />

          {/* Submit */}
          <button
            onClick={handleUpload}
            disabled={loading || (!file && !textInput.trim())}
            style={{
              width: '100%',
              padding: 14,
              borderRadius: 10,
              border: 'none',
              background: loading ? textSecondary : accent,
              color: '#fff',
              fontSize: 16,
              fontWeight: 600,
              cursor: loading ? 'wait' : 'pointer',
              opacity: (!file && !textInput.trim()) ? 0.5 : 1,
            }}
          >
            {loading
              ? (lang === 'es' ? 'Analizando...' : 'Analyzing...')
              : (lang === 'es' ? 'Analizar con IA' : 'Analyze with AI')}
          </button>

          {/* Error */}
          {error && (
            <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: '#FEF2F2', border: `1px solid ${red}`, color: red, fontSize: 14 }}>
              {error}
            </div>
          )}

          {/* Results */}
          {result && !error && <ResultCard result={result} lang={lang} isDark={isDark} />}
        </div>
      )}

      {/* TAB: Drive */}
      {tab === 'drive' && (
        <div>
          {/* Search bar with autocomplete */}
          <div style={{ position: 'relative', marginBottom: 16 }}>
            <input
              value={driveSearch}
              onChange={(e) => setDriveSearch(e.target.value)}
              placeholder={lang === 'es' ? 'Buscar archivo por nombre...' : 'Search file by name...'}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 10,
                border: `2px solid ${driveSearch ? accent : border}`,
                background: bgCard,
                color: textPrimary,
                fontSize: 15,
                boxSizing: 'border-box',
                outline: 'none',
              }}
            />
            {driveSearch && driveFiles.length > 0 && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
                background: bg, border: `1px solid ${border}`, borderRadius: 8,
                maxHeight: 200, overflowY: 'auto', marginTop: 4, boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              }}>
                {driveFiles
                  .filter(f => f.name.toLowerCase().includes(driveSearch.toLowerCase()))
                  .map(f => (
                    <div
                      key={f.id}
                      onClick={() => { setDriveSearch(''); handleDriveProcess(f.id, f.name) }}
                      style={{
                        padding: '10px 14px', cursor: 'pointer', fontSize: 14, color: textPrimary,
                        borderBottom: `1px solid ${border}`,
                      }}
                      onMouseOver={(e) => e.currentTarget.style.background = isDark ? '#2A2D35' : '#EFF6FF'}
                      onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <span style={{ fontWeight: 600 }}>{f.name}</span>
                      <span style={{ color: textSecondary, fontSize: 12, marginLeft: 8 }}>
                        {f.mimeType?.split('/').pop()}
                      </span>
                    </div>
                  ))}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <p style={{ color: textSecondary, fontSize: 14, margin: 0 }}>
              {lang === 'es' ? 'O selecciona un archivo:' : 'Or select a file:'}
            </p>
            <button
              onClick={loadDriveFiles}
              style={{ padding: '6px 12px', borderRadius: 6, border: `1px solid ${border}`, background: bgCard, color: textPrimary, fontSize: 13, cursor: 'pointer' }}
            >
              {lang === 'es' ? 'Refrescar' : 'Refresh'}
            </button>
          </div>

          {driveLoading ? (
            <p style={{ color: textSecondary, textAlign: 'center', padding: 40 }}>
              {lang === 'es' ? 'Cargando archivos de Drive...' : 'Loading Drive files...'}
            </p>
          ) : driveFiles.length === 0 ? (
            <p style={{ color: textSecondary, textAlign: 'center', padding: 40 }}>
              {lang === 'es' ? 'No se encontraron archivos' : 'No files found'}
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {driveFiles.filter(f => !driveSearch || f.name.toLowerCase().includes(driveSearch.toLowerCase())).map(f => (
                <div
                  key={f.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px 16px',
                    borderRadius: 10,
                    border: `1px solid ${border}`,
                    background: bgCard,
                  }}
                >
                  <div>
                    <p style={{ margin: 0, fontWeight: 600, fontSize: 15, color: textPrimary }}>{f.name}</p>
                    <p style={{ margin: '2px 0 0', fontSize: 12, color: textSecondary }}>
                      {f.mimeType?.split('/').pop() || 'file'} — {f.modifiedTime ? new Date(f.modifiedTime).toLocaleDateString() : ''}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDriveProcess(f.id, f.name)}
                    disabled={loading}
                    style={{
                      padding: '8px 16px',
                      borderRadius: 8,
                      border: 'none',
                      background: accent,
                      color: '#fff',
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: loading ? 'wait' : 'pointer',
                    }}
                  >
                    {loading ? '...' : (lang === 'es' ? 'Analizar' : 'Analyze')}
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Show result if processing from drive */}
          {result && <ResultCard result={result} lang={lang} isDark={isDark} />}
        </div>
      )}

      {/* TAB: History */}
      {tab === 'history' && (
        <div>
          {historyLoading ? (
            <p style={{ color: textSecondary, textAlign: 'center', padding: 40 }}>
              {lang === 'es' ? 'Cargando historial...' : 'Loading history...'}
            </p>
          ) : runs.length === 0 ? (
            <p style={{ color: textSecondary, textAlign: 'center', padding: 40 }}>
              {lang === 'es' ? 'Sin ejecuciones aun' : 'No runs yet'}
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {runs.map(r => (
                <div
                  key={r.id}
                  style={{
                    padding: '12px 16px',
                    borderRadius: 10,
                    border: `1px solid ${border}`,
                    background: bgCard,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <p style={{ margin: 0, fontWeight: 600, fontSize: 15, color: textPrimary }}>
                        {r.file_name || r.pipeline_name}
                      </p>
                      <p style={{ margin: '2px 0 0', fontSize: 12, color: textSecondary }}>
                        {r.document_type || ''} — {r.created_at ? new Date(r.created_at).toLocaleString() : ''}
                      </p>
                    </div>
                    <span style={{
                      padding: '4px 10px',
                      borderRadius: 20,
                      fontSize: 12,
                      fontWeight: 600,
                      background: r.status === 'completed' ? '#D1FAE5' : '#FEE2E2',
                      color: r.status === 'completed' ? '#065F46' : '#991B1B',
                    }}>
                      {r.status}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 13, color: textSecondary }}>
                    <span>{r.total_tokens || 0} tokens</span>
                    <span>${(r.cost_usd || r.total_cost || 0).toFixed(4)}</span>
                    <span>{r.processing_time_ms || 0}ms</span>
                    {r.notion_url && (
                      <a href={r.notion_url} target="_blank" rel="noopener" style={{ color: accent }}>Notion</a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Result Card Component ── */
function ResultCard({ result, lang, isDark }) {
  const bg = isDark ? '#22252B' : '#F9FAFB'
  const border = isDark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'
  const textPrimary = isDark ? '#F3F4F6' : '#111827'
  const textSecondary = isDark ? '#9CA3AF' : '#6B7280'
  const accent = '#2563EB'
  const green = '#10B981'

  return (
    <div style={{ marginTop: 24, borderRadius: 12, border: `1px solid ${border}`, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ background: 'linear-gradient(135deg, #0F172A, #1E40AF)', padding: '16px 20px', color: '#fff' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 18 }}>{result.file_name || 'Analysis'}</h3>
            <p style={{ margin: '4px 0 0', fontSize: 13, opacity: 0.8 }}>
              {result.document_type?.toUpperCase()} — {result.processing_time_ms?.toFixed(0)}ms
            </p>
          </div>
          <span style={{
            padding: '4px 12px',
            borderRadius: 20,
            fontSize: 12,
            fontWeight: 600,
            background: result.status === 'completed' || result.status === 'success' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
            color: result.status === 'completed' || result.status === 'success' ? '#6EE7B7' : '#FCA5A5',
          }}>
            {result.status}
          </span>
        </div>
      </div>

      <div style={{ padding: 20, background: bg }}>
        {/* Metrics row */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          {[
            { label: 'Tokens', value: result.total_tokens || 0 },
            { label: lang === 'es' ? 'Costo' : 'Cost', value: `$${(result.cost_usd || result.total_cost || 0).toFixed(4)}` },
            { label: lang === 'es' ? 'Agentes' : 'Agents', value: result.agents_used?.length || 0 },
            { label: 'Email', value: result.email_sent ? 'Sent' : 'No' },
          ].map(m => (
            <div key={m.label} style={{
              padding: '8px 14px',
              borderRadius: 8,
              background: isDark ? '#1A1D23' : '#EFF6FF',
              fontSize: 13,
            }}>
              <span style={{ color: textSecondary }}>{m.label}: </span>
              <span style={{ color: textPrimary, fontWeight: 600 }}>{m.value}</span>
            </div>
          ))}
        </div>

        {/* Summary */}
        {result.summary && (
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ margin: '0 0 6px', fontSize: 15, color: textPrimary }}>
              {lang === 'es' ? 'Resumen' : 'Summary'}
            </h4>
            <p style={{ margin: 0, color: textSecondary, lineHeight: 1.6, fontSize: 14 }}>{result.summary}</p>
          </div>
        )}

        {/* Q&A */}
        {result.questions?.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ margin: '0 0 8px', fontSize: 15, color: textPrimary }}>
              {lang === 'es' ? 'Preguntas y Respuestas' : 'Questions & Answers'}
            </h4>
            {result.questions.map((q, i) => (
              <div key={i} style={{
                padding: 12,
                borderRadius: 8,
                background: isDark ? '#1A1D23' : '#F8FAFC',
                borderLeft: `3px solid ${accent}`,
                marginBottom: 8,
              }}>
                <p style={{ margin: 0, fontWeight: 600, fontSize: 14, color: textPrimary }}>
                  Q: {q.question}
                </p>
                <p style={{ margin: '6px 0 0', fontSize: 14, color: textSecondary }}>
                  A: {result.answers?.[i]?.answer || 'N/A'}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Pipeline steps */}
        {result.pipeline_steps?.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ margin: '0 0 8px', fontSize: 15, color: textPrimary }}>Pipeline</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {result.pipeline_steps.map((s, i) => (
                <div key={i} style={{ fontSize: 13, color: textSecondary, fontFamily: 'monospace' }}>
                  {s.includes('success') || s.includes('ok') ? '✓' : s.includes('error') || s.includes('fail') ? '✗' : '→'} {s}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Links */}
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {result.notion_url && (
            <a href={result.notion_url} target="_blank" rel="noopener"
              style={{ padding: '8px 16px', borderRadius: 8, background: accent, color: '#fff', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}>
              {lang === 'es' ? 'Ver en Notion' : 'View in Notion'}
            </a>
          )}
          {result.whatsapp_link && (
            <a href={result.whatsapp_link} target="_blank" rel="noopener"
              style={{ padding: '8px 16px', borderRadius: 8, background: green, color: '#fff', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}>
              WhatsApp
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
