import { useState, useEffect, useCallback } from 'react'
import { fetchAPI } from '../../../services/api'
import { useCtrlEnter } from '../../../shared/hooks/useCtrlEnter'
import StatsBar from './StatsBar'
import ResultsTable from './ResultsTable'
import AutoDashboardGenerator from './AutoDashboardGenerator'

function formatDate(iso, lang) {
  if (!iso) return '--'
  return new Date(iso).toLocaleString(lang === 'es' ? 'es-ES' : 'en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function JsonViewer({ data, label }) {
  const [expanded, setExpanded] = useState(false)
  const str = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
  const preview = str.length > 120 ? str.slice(0, 120) + '...' : str

  return (
    <div style={{ marginBottom: 12 }}>
      {label && (
        <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase' }}>
          {label}
        </p>
      )}
      <div
        onClick={() => str.length > 120 && setExpanded(e => !e)}
        style={{
          padding: 12, background: '#F9FAFB', borderRadius: 8,
          border: '1px solid #E5E7EB', fontSize: 12, fontFamily: 'monospace',
          color: '#374151', lineHeight: 1.6, whiteSpace: 'pre-wrap',
          wordBreak: 'break-word', cursor: str.length > 120 ? 'pointer' : 'default',
          maxHeight: expanded ? 'none' : 200, overflow: 'hidden',
        }}
      >
        {expanded ? str : preview}
      </div>
      {str.length > 120 && (
        <button
          onClick={() => setExpanded(e => !e)}
          style={{
            background: 'none', border: 'none', padding: '4px 0',
            fontSize: 11, color: '#6366F1', cursor: 'pointer', fontWeight: 500,
          }}
        >
          {expanded ? '▲ Collapse' : '▼ Expand'}
        </button>
      )}
    </div>
  )
}

export default function GenericDashboard({ automation, lang, onBack }) {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [selectedResult, setSelectedResult] = useState(null)
  const [error, setError] = useState(null)
  const [isMobile, setIsMobile] = useState(false)

  // Input state based on automation config
  const inputType = automation.input_config?.type || 'text'
  const [textInput, setTextInput] = useState('')
  const [jsonInput, setJsonInput] = useState('{\n  \n}')
  const [formValues, setFormValues] = useState({})

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

  // Ctrl+Enter to process
  useCtrlEnter(() => { if (isInputValid() && !processing) handleProcess() }, !processing)

  const getInputData = () => {
    if (inputType === 'json') {
      try { return JSON.parse(jsonInput) } catch { return { raw: jsonInput } }
    }
    if (inputType === 'form') return formValues
    return { text: textInput.trim() }
  }

  const isInputValid = () => {
    if (inputType === 'json') {
      try { JSON.parse(jsonInput); return true } catch { return false }
    }
    if (inputType === 'form') {
      const fields = automation.input_config?.fields || []
      return fields.filter(f => f.required).every(f => formValues[f.name]?.toString().trim())
    }
    return textInput.trim().length > 0
  }

  const handleProcess = async () => {
    if (!isInputValid() || processing) return
    setProcessing(true)
    setError(null)

    try {
      const input_data = getInputData()
      const runRes = await fetchAPI(`/automations/${automation.id}/run`, {
        method: 'POST',
        body: JSON.stringify({ input_data }),
      })

      if (runRes.error) {
        setError(runRes.error)
        setProcessing(false)
        return
      }

      const runId = runRes.data?.run_id
      if (!runId) {
        setError(lang === 'es' ? 'No se obtuvo ID de ejecucion' : 'No run ID returned')
        setProcessing(false)
        return
      }

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
              input_data,
              output_data: output,
              result_type: 'generic',
            }),
          })
          setTextInput('')
          setJsonInput('{\n  \n}')
          setFormValues({})
          await loadResults()
          setProcessing(false)
          try {
            const { addNotification } = await import('../../../shared/components/NotificationBell')
            addNotification(lang === 'es' ? 'Procesamiento completado' : 'Processing complete', 'success')
          } catch {}
        } else if (status === 'failed') {
          setError(execRes.data?.error || (lang === 'es' ? 'La ejecucion fallo' : 'Execution failed'))
          setProcessing(false)
          try {
            const { addNotification } = await import('../../../shared/components/NotificationBell')
            addNotification(lang === 'es' ? 'Error en procesamiento' : 'Processing failed', 'error')
          } catch {}
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

  const color = automation.color || '#6366F1'
  const totalRuns = results.length
  const successCount = results.filter(r => r.output_data && Object.keys(r.output_data).length > 0).length
  const successRate = totalRuns > 0 ? Math.round((successCount / totalRuns) * 100) : 0

  const statsData = [
    { label: lang === 'es' ? 'Total ejecutado' : 'Total runs', value: totalRuns, color: '#6366F1' },
    { label: lang === 'es' ? 'Tasa de exito' : 'Success rate', value: `${successRate}%`, color: '#10B981' },
    { label: lang === 'es' ? 'Ultimo resultado' : 'Last result', value: results.length > 0 ? formatDate(results[0].created_at, lang) : '--', color: '#F59E0B' },
  ]

  const columns = [
    { key: 'date', label: lang === 'es' ? 'Fecha' : 'Date' },
    { key: 'status', label: lang === 'es' ? 'Estado' : 'Status' },
    { key: 'input_preview', label: 'Input', maxWidth: 180 },
    { key: 'output_preview', label: 'Output', maxWidth: 200 },
  ]

  const renderCell = (row, key) => {
    switch (key) {
      case 'date': return formatDate(row.created_at, lang)
      case 'status': {
        const hasOutput = row.output_data && Object.keys(row.output_data).length > 0
        return (
          <span style={{
            padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 500,
            background: hasOutput ? '#D1FAE5' : '#FEE2E2',
            color: hasOutput ? '#059669' : '#DC2626',
          }}>
            {hasOutput ? (lang === 'es' ? 'Completado' : 'Completed') : (lang === 'es' ? 'Error' : 'Error')}
          </span>
        )
      }
      case 'input_preview': {
        const inp = row.input_data || {}
        const preview = inp.text || JSON.stringify(inp).slice(0, 60)
        return (
          <span style={{ color: '#6B7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block', maxWidth: 180 }}>
            {preview.length > 60 ? preview.slice(0, 57) + '...' : preview}
          </span>
        )
      }
      case 'output_preview': {
        const out = row.output_data || {}
        const preview = out.text || out.result || out.summary || JSON.stringify(out).slice(0, 60)
        return (
          <span style={{ color: '#6B7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block', maxWidth: 200 }}>
            {typeof preview === 'string' && preview.length > 60 ? preview.slice(0, 57) + '...' : preview}
          </span>
        )
      }
      default: return '--'
    }
  }

  // Detail view — uses AutoDashboardGenerator for dynamic visualization
  if (selectedResult) {
    return (
      <div style={{ animation: 'fadeIn 0.2s ease-out' }}>
        <button onClick={() => setSelectedResult(null)} style={{
          background: '#F3F4F6', border: 'none', borderRadius: 8,
          padding: '8px 16px', cursor: 'pointer', fontSize: 13,
          color: '#6B7280', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span>\u2190</span> {lang === 'es' ? 'Volver a resultados' : 'Back to results'}
        </button>

        <div style={{
          background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
          padding: 24, marginBottom: 16,
        }}>
          <div style={{ marginBottom: 16, paddingBottom: 12, borderBottom: '1px solid #E5E7EB' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: '#111827', margin: '0 0 4px' }}>
              {lang === 'es' ? 'Detalle del resultado' : 'Result detail'}
            </h3>
            <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0 }}>
              {formatDate(selectedResult.created_at, lang)}
            </p>
          </div>

          <JsonViewer data={selectedResult.input_data} label="Input" />
        </div>

        {/* Auto-generated dashboard from output data */}
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ fontSize: 13, fontWeight: 600, color: '#374151', margin: '0 0 12px' }}>
            {lang === 'es' ? 'Visualizacion automatica' : 'Auto visualization'}
          </h4>
          <AutoDashboardGenerator outputData={selectedResult.output_data} lang={lang} />
        </div>

        {/* Raw output fallback */}
        <div style={{ marginTop: 16 }}>
          <JsonViewer data={selectedResult.output_data} label={lang === 'es' ? 'Datos crudos' : 'Raw data'} />
        </div>
      </div>
    )
  }

  const formFields = automation.input_config?.fields || []

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
          {automation.icon || '⚡'}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: '#111827', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {automation.name}
          </h1>
          <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0 }}>
            {automation.description || automation.workflow_name}
          </p>
        </div>
      </div>

      <StatsBar stats={statsData} lang={lang} />

      {/* Input Panel */}
      <div style={{
        background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
        padding: isMobile ? 16 : 20, marginBottom: 24,
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: '0 0 12px' }}>
          {lang === 'es' ? 'Nueva ejecucion' : 'New execution'}
        </h3>

        {inputType === 'form' && formFields.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, 1fr)', gap: 12 }}>
            {formFields.map(field => (
              <div key={field.name}>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 4 }}>
                  {field.label || field.name}
                  {field.required && <span style={{ color: '#DC2626' }}> *</span>}
                </label>
                {field.type === 'textarea' ? (
                  <textarea
                    value={formValues[field.name] || ''}
                    onChange={e => setFormValues(prev => ({ ...prev, [field.name]: e.target.value }))}
                    placeholder={field.placeholder || ''}
                    style={{
                      width: '100%', minHeight: 60, padding: '8px 10px', borderRadius: 8,
                      border: '1px solid #E5E7EB', fontSize: 13, color: '#374151',
                      boxSizing: 'border-box', outline: 'none', resize: 'vertical',
                    }}
                  />
                ) : field.type === 'select' ? (
                  <select
                    value={formValues[field.name] || ''}
                    onChange={e => setFormValues(prev => ({ ...prev, [field.name]: e.target.value }))}
                    style={{
                      width: '100%', padding: '8px 10px', borderRadius: 8,
                      border: '1px solid #E5E7EB', fontSize: 13, color: '#374151',
                      background: '#fff', boxSizing: 'border-box', outline: 'none',
                    }}
                  >
                    <option value="">{lang === 'es' ? 'Seleccionar...' : 'Select...'}</option>
                    {(field.options || []).map(o => (
                      <option key={o.value || o} value={o.value || o}>{o.label || o}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={field.type || 'text'}
                    value={formValues[field.name] || ''}
                    onChange={e => setFormValues(prev => ({ ...prev, [field.name]: e.target.value }))}
                    placeholder={field.placeholder || ''}
                    style={{
                      width: '100%', padding: '8px 10px', borderRadius: 8,
                      border: '1px solid #E5E7EB', fontSize: 13, color: '#374151',
                      boxSizing: 'border-box', outline: 'none',
                    }}
                  />
                )}
              </div>
            ))}
          </div>
        ) : inputType === 'json' ? (
          <textarea
            value={jsonInput}
            onChange={e => setJsonInput(e.target.value)}
            placeholder='{"key": "value"}'
            style={{
              width: '100%', minHeight: 100, padding: 12, borderRadius: 8,
              border: '1px solid #E5E7EB', fontSize: 12, fontFamily: 'monospace',
              color: '#374151', resize: 'vertical', lineHeight: 1.6,
              boxSizing: 'border-box', outline: 'none',
            }}
            onFocus={e => e.target.style.borderColor = color}
            onBlur={e => e.target.style.borderColor = '#E5E7EB'}
          />
        ) : (
          <textarea
            value={textInput}
            onChange={e => setTextInput(e.target.value)}
            placeholder={lang === 'es'
              ? 'Ingresa los datos de entrada...'
              : 'Enter input data...'}
            style={{
              width: '100%', minHeight: 80, padding: 12, borderRadius: 8,
              border: '1px solid #E5E7EB', fontSize: 13, fontFamily: 'inherit',
              color: '#374151', resize: 'vertical', lineHeight: 1.6,
              boxSizing: 'border-box', outline: 'none',
            }}
            onFocus={e => e.target.style.borderColor = color}
            onBlur={e => e.target.style.borderColor = '#E5E7EB'}
          />
        )}

        {error && (
          <div style={{ marginTop: 8, padding: '8px 12px', borderRadius: 8, background: '#FEF2F2', border: '1px solid #FECACA', fontSize: 12, color: '#DC2626' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
          <button
            onClick={handleProcess}
            disabled={!isInputValid() || processing}
            style={{
              padding: '9px 20px', borderRadius: 8, border: 'none',
              fontSize: 13, fontWeight: 600, color: '#fff',
              background: (!isInputValid() || processing) ? '#A5B4FC' : `linear-gradient(135deg, ${color}, #8B5CF6)`,
              cursor: (!isInputValid() || processing) ? 'default' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            {processing && (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ animation: 'spin 1s linear infinite' }}>
                <path d="M21 12a9 9 0 11-6.219-8.56" />
              </svg>
            )}
            {processing
              ? (lang === 'es' ? 'Ejecutando...' : 'Running...')
              : (lang === 'es' ? 'Ejecutar' : 'Run')}
          </button>
        </div>
      </div>

      {/* Results */}
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: '0 0 12px' }}>
          {lang === 'es' ? 'Resultados' : 'Results'}
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
      ) : (
        <ResultsTable
          results={results}
          columns={columns}
          lang={lang}
          onRowClick={setSelectedResult}
          renderCell={renderCell}
          emptyIcon="⚡"
          emptyTitle={lang === 'es' ? 'Sin resultados' : 'No results'}
          emptyDescription={lang === 'es'
            ? 'Ejecuta la automatizacion arriba para ver resultados.'
            : 'Run the automation above to see results.'}
        />
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } } @keyframes fadeIn { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none } }`}</style>
    </div>
  )
}
