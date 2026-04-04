import { useState, useEffect, useCallback } from 'react'
import { fetchAPI } from '../../../services/api'
import StatsBar from './StatsBar'
import ResultsTable from './ResultsTable'

function formatDate(iso, lang) {
  if (!iso) return '--'
  return new Date(iso).toLocaleString(lang === 'es' ? 'es-ES' : 'en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function ConfidencePill({ value }) {
  const pct = Math.round((value || 0) * 100)
  const color = pct >= 80 ? '#059669' : pct >= 50 ? '#D97706' : '#DC2626'
  const bg = pct >= 80 ? '#D1FAE5' : pct >= 50 ? '#FEF3C7' : '#FEE2E2'
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600,
      background: bg, color, whiteSpace: 'nowrap',
    }}>
      {pct}%
    </span>
  )
}

export default function EmailDashboard({ automation, lang, onBack }) {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [emailText, setEmailText] = useState('')
  const [selectedResult, setSelectedResult] = useState(null)
  const [error, setError] = useState(null)
  const [isMobile, setIsMobile] = useState(false)

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

  const handleProcess = async () => {
    if (!emailText.trim() || processing) return
    setProcessing(true)
    setError(null)

    try {
      const runRes = await fetchAPI(`/automations/${automation.id}/run`, {
        method: 'POST',
        body: JSON.stringify({ input_data: { text: emailText.trim(), type: 'email' } }),
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
              input_data: { text: emailText.trim() },
              output_data: output,
              result_type: 'email',
            }),
          })
          setEmailText('')
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

  const color = automation.color || '#8B5CF6'
  const totalEmails = results.length
  const autoResolved = results.filter(r => r.output_data?.auto_resolved || r.output_data?.status === 'auto').length
  const escalated = results.filter(r => r.output_data?.escalated || r.output_data?.status === 'escalated').length
  const autoRate = totalEmails > 0 ? Math.round((autoResolved / totalEmails) * 100) : 0

  const stats = [
    { label: lang === 'es' ? 'Emails procesados' : 'Emails processed', value: totalEmails, color: '#8B5CF6' },
    { label: lang === 'es' ? 'Auto-resueltos' : 'Auto-resolved', value: `${autoRate}%`, color: '#10B981' },
    { label: lang === 'es' ? 'Escalados' : 'Escalated', value: escalated, color: '#F59E0B' },
    { label: lang === 'es' ? 'Confianza prom.' : 'Avg confidence', value: totalEmails > 0
      ? `${Math.round(results.reduce((sum, r) => sum + ((r.output_data?.confidence || 0.75) * 100), 0) / totalEmails)}%`
      : '--', color: '#6366F1' },
  ]

  const columns = [
    { key: 'date', label: lang === 'es' ? 'Fecha' : 'Date' },
    { key: 'intent', label: lang === 'es' ? 'Intencion' : 'Intent' },
    { key: 'confidence', label: lang === 'es' ? 'Confianza' : 'Confidence' },
    { key: 'response_preview', label: lang === 'es' ? 'Respuesta' : 'Response', maxWidth: 200 },
    { key: 'status', label: lang === 'es' ? 'Estado' : 'Status' },
  ]

  const renderCell = (row, key) => {
    const out = row.output_data || {}
    switch (key) {
      case 'date': return formatDate(row.created_at, lang)
      case 'intent': return (
        <span style={{
          padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 500,
          background: '#EEF2FF', color: '#4338CA',
        }}>
          {out.intent || out.category || '--'}
        </span>
      )
      case 'confidence': return <ConfidencePill value={out.confidence} />
      case 'response_preview': {
        const preview = out.response || out.auto_response || '--'
        return (
          <span style={{ color: '#6B7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block', maxWidth: 200 }}>
            {preview.slice(0, 60)}{preview.length > 60 ? '...' : ''}
          </span>
        )
      }
      case 'status': {
        const isAuto = out.auto_resolved || out.status === 'auto'
        return (
          <span style={{
            padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 500,
            background: isAuto ? '#D1FAE5' : '#FEF3C7',
            color: isAuto ? '#059669' : '#D97706',
          }}>
            {isAuto
              ? (lang === 'es' ? 'Auto' : 'Auto')
              : (lang === 'es' ? 'Escalado' : 'Escalated')}
          </span>
        )
      }
      default: return '--'
    }
  }

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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: '#111827', margin: 0 }}>
              {lang === 'es' ? 'Analisis del Email' : 'Email Analysis'}
            </h3>
            <div style={{ display: 'flex', gap: 8 }}>
              {out.intent && (
                <span style={{
                  padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                  background: '#EEF2FF', color: '#4338CA',
                }}>
                  {out.intent}
                </span>
              )}
              <ConfidencePill value={out.confidence} />
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase' }}>
              {lang === 'es' ? 'Email original' : 'Original email'}
            </p>
            <div style={{
              padding: 12, background: '#F9FAFB', borderRadius: 8,
              border: '1px solid #E5E7EB', fontSize: 13, color: '#374151',
              lineHeight: 1.6, whiteSpace: 'pre-wrap',
            }}>
              {inp.text || '--'}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase' }}>
                {lang === 'es' ? 'Intencion detectada' : 'Detected intent'}
              </p>
              <p style={{ fontSize: 14, color: '#374151', margin: 0 }}>{out.intent || out.category || '--'}</p>
            </div>
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase' }}>
                {lang === 'es' ? 'Sentimiento' : 'Sentiment'}
              </p>
              <p style={{ fontSize: 14, color: '#374151', margin: 0 }}>{out.sentiment || '--'}</p>
            </div>
          </div>

          {out.classification_details && (
            <div style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 8, textTransform: 'uppercase' }}>
                {lang === 'es' ? 'Detalles de clasificacion' : 'Classification details'}
              </p>
              <div style={{
                padding: 12, background: '#F9FAFB', borderRadius: 8,
                border: '1px solid #E5E7EB', fontSize: 12, fontFamily: 'monospace',
                color: '#374151', lineHeight: 1.6, whiteSpace: 'pre-wrap',
              }}>
                {typeof out.classification_details === 'string'
                  ? out.classification_details
                  : JSON.stringify(out.classification_details, null, 2)}
              </div>
            </div>
          )}

          <div>
            <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase' }}>
              {lang === 'es' ? 'Respuesta generada' : 'Generated response'}
            </p>
            <div style={{
              padding: 12,
              background: (out.auto_resolved || out.status === 'auto') ? '#F0FDF4' : '#FFFBEB',
              borderRadius: 8,
              border: `1px solid ${(out.auto_resolved || out.status === 'auto') ? '#BBF7D0' : '#FDE68A'}`,
              fontSize: 13,
              color: (out.auto_resolved || out.status === 'auto') ? '#166534' : '#92400E',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
            }}>
              {out.response || out.auto_response || (lang === 'es' ? 'Sin respuesta generada' : 'No response generated')}
            </div>
          </div>
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
          {automation.icon || '📧'}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: '#111827', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {automation.name}
          </h1>
          <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0 }}>
            {lang === 'es' ? 'Respuesta inteligente de emails' : 'Intelligent email responder'}
          </p>
        </div>
      </div>

      <StatsBar stats={stats} lang={lang} />

      {/* Input Panel */}
      <div style={{
        background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
        padding: isMobile ? 16 : 20, marginBottom: 24,
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: '0 0 12px' }}>
          {lang === 'es' ? 'Procesar nuevo email' : 'Process new email'}
        </h3>
        <textarea
          value={emailText}
          onChange={e => setEmailText(e.target.value)}
          placeholder={lang === 'es'
            ? 'Pega el contenido del email aqui...\n\nEj: "Hola, compre el producto X hace 2 semanas y todavia no lo recibo. Mi numero de orden es #12345. Necesito saber cuando llegara o quiero un reembolso."'
            : 'Paste email content here...\n\nE.g.: "Hi, I purchased product X 2 weeks ago and still haven\'t received it. My order number is #12345. I need to know when it will arrive or I want a refund."'}
          style={{
            width: '100%', minHeight: 100, padding: 12, borderRadius: 8,
            border: '1px solid #E5E7EB', fontSize: 13, fontFamily: 'inherit',
            color: '#374151', resize: 'vertical', lineHeight: 1.6,
            boxSizing: 'border-box', outline: 'none',
          }}
          onFocus={e => e.target.style.borderColor = color}
          onBlur={e => e.target.style.borderColor = '#E5E7EB'}
        />
        {error && (
          <div style={{ marginTop: 8, padding: '8px 12px', borderRadius: 8, background: '#FEF2F2', border: '1px solid #FECACA', fontSize: 12, color: '#DC2626' }}>
            {error}
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
          <button
            onClick={handleProcess}
            disabled={!emailText.trim() || processing}
            style={{
              padding: '9px 20px', borderRadius: 8, border: 'none',
              fontSize: 13, fontWeight: 600, color: '#fff',
              background: (!emailText.trim() || processing) ? '#C4B5FD' : `linear-gradient(135deg, ${color}, #6366F1)`,
              cursor: (!emailText.trim() || processing) ? 'default' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            {processing && (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ animation: 'spin 1s linear infinite' }}>
                <path d="M21 12a9 9 0 11-6.219-8.56" />
              </svg>
            )}
            {processing
              ? (lang === 'es' ? 'Generando...' : 'Generating...')
              : (lang === 'es' ? 'Generar Respuesta' : 'Generate Response')}
          </button>
        </div>
      </div>

      {/* Results */}
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: '0 0 12px' }}>
          {lang === 'es' ? 'Emails procesados' : 'Processed emails'}
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
          emptyIcon="📧"
          emptyTitle={lang === 'es' ? 'Sin emails procesados' : 'No emails processed'}
          emptyDescription={lang === 'es'
            ? 'Pega el contenido de un email arriba para generar una respuesta automatica.'
            : 'Paste email content above to generate an automatic response.'}
        />
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } } @keyframes fadeIn { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none } }`}</style>
    </div>
  )
}
