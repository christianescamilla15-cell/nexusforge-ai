import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

export default function RunInputModal({ automation, onSubmit, onClose, lang = 'en' }) {
  const config = automation.input_config || { type: 'none' }
  const [text, setText] = useState('')
  const [jsonText, setJsonText] = useState('{}')
  const [formValues, setFormValues] = useState({})
  const [jsonError, setJsonError] = useState(null)
  // Drive/Sheets/API state
  const [driveFiles, setDriveFiles] = useState([])
  const [selectedFileId, setSelectedFileId] = useState('')
  const [driveFolderId, setDriveFolderId] = useState('')
  const [sheetsUrl, setSheetsUrl] = useState('')
  const [sheetsRange, setSheetsRange] = useState('A1:Z1000')
  const [apiEndpoint, setApiEndpoint] = useState('')
  const [apiHeaders, setApiHeaders] = useState('{}')
  const [loadingFiles, setLoadingFiles] = useState(false)

  // Load Drive files when input is drive
  useEffect(() => {
    if (config.type === 'drive') {
      setLoadingFiles(true)
      fetchAPI('/workflows/drive-to-intelligence/files').then(res => {
        if (!res.error && res.data?.files) setDriveFiles(res.data.files)
        setLoadingFiles(false)
      }).catch(() => setLoadingFiles(false))
    }
  }, [config.type])

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
        setJsonError(lang === 'es' ? 'JSON inv\u00E1lido' : 'Invalid JSON')
        return
      }
    } else if (config.type === 'form') {
      input_data = { ...formValues }
    } else if (config.type === 'drive') {
      input_data = { source: 'drive', file_id: selectedFileId, folder_id: driveFolderId }
    } else if (config.type === 'sheets') {
      input_data = { source: 'sheets', spreadsheet_url: sheetsUrl, range: sheetsRange }
    } else if (config.type === 'api') {
      let headers = {}
      try { headers = JSON.parse(apiHeaders) } catch {}
      input_data = { source: 'api', endpoint: apiEndpoint, headers }
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

        {/* Google Drive input */}
        {config.type === 'drive' && (
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 8 }}>
              {lang === 'es' ? 'Selecciona archivo de Drive' : 'Select Drive file'}
            </label>
            {loadingFiles ? (
              <p style={{ fontSize: 13, color: '#9CA3AF' }}>{lang === 'es' ? 'Cargando archivos...' : 'Loading files...'}</p>
            ) : driveFiles.length > 0 ? (
              <select
                value={selectedFileId}
                onChange={e => setSelectedFileId(e.target.value)}
                style={inputStyle}
              >
                <option value="">{lang === 'es' ? 'Seleccionar archivo...' : 'Select file...'}</option>
                {driveFiles.map(f => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
            ) : (
              <p style={{ fontSize: 12, color: '#EF4444' }}>
                {lang === 'es' ? 'No se encontraron archivos. Verifica la integraci\u00F3n de Google Drive.' : 'No files found. Check Google Drive integration.'}
              </p>
            )}
            <div style={{ marginTop: 10 }}>
              <label style={{ fontSize: 12, color: '#6B7280', display: 'block', marginBottom: 4 }}>
                {lang === 'es' ? 'Folder ID (opcional)' : 'Folder ID (optional)'}
              </label>
              <input
                type="text"
                value={driveFolderId}
                onChange={e => setDriveFolderId(e.target.value)}
                placeholder="1P56v2fk..."
                style={{ ...inputStyle, fontSize: 12 }}
              />
            </div>
          </div>
        )}

        {/* Google Sheets input */}
        {config.type === 'sheets' && (
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 8 }}>
              {lang === 'es' ? 'URL del Google Sheet' : 'Google Sheet URL'}
            </label>
            <input
              type="text"
              value={sheetsUrl}
              onChange={e => setSheetsUrl(e.target.value)}
              placeholder="https://docs.google.com/spreadsheets/d/..."
              style={inputStyle}
              autoFocus
            />
            <div style={{ marginTop: 10 }}>
              <label style={{ fontSize: 12, color: '#6B7280', display: 'block', marginBottom: 4 }}>
                {lang === 'es' ? 'Rango de celdas' : 'Cell range'}
              </label>
              <input
                type="text"
                value={sheetsRange}
                onChange={e => setSheetsRange(e.target.value)}
                placeholder="A1:Z1000"
                style={{ ...inputStyle, fontSize: 12 }}
              />
            </div>
          </div>
        )}

        {/* External API input */}
        {config.type === 'api' && (
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 8 }}>
              {lang === 'es' ? 'Endpoint de la API' : 'API Endpoint'}
            </label>
            <input
              type="text"
              value={apiEndpoint}
              onChange={e => setApiEndpoint(e.target.value)}
              placeholder="https://api.zendesk.com/v2/tickets.json"
              style={inputStyle}
              autoFocus
            />
            <div style={{ marginTop: 10 }}>
              <label style={{ fontSize: 12, color: '#6B7280', display: 'block', marginBottom: 4 }}>
                {lang === 'es' ? 'Headers (JSON)' : 'Headers (JSON)'}
              </label>
              <textarea
                value={apiHeaders}
                onChange={e => setApiHeaders(e.target.value)}
                placeholder='{"Authorization": "Bearer token..."}'
                rows={3}
                style={{ ...inputStyle, fontFamily: 'monospace', fontSize: 11, resize: 'vertical' }}
              />
            </div>
          </div>
        )}

        {/* No input needed */}
        {(config.type === 'none' || config.type === 'webhook' || config.type === 'email') && (
          <p style={{ fontSize: 13, color: '#6B7280', marginBottom: 20, textAlign: 'center' }}>
            {config.type === 'webhook'
              ? (lang === 'es' ? 'Esta automatizaci\u00F3n se activa v\u00EDa webhook externo' : 'This automation triggers via external webhook')
              : config.type === 'email'
              ? (lang === 'es' ? 'Esta automatizaci\u00F3n se activa cuando llega un email' : 'This automation triggers on incoming email')
              : (lang === 'es' ? 'No requiere datos de entrada' : 'No input data required')}
          </p>
        )}

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
