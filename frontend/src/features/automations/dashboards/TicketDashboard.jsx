import { useState, useEffect, useCallback } from 'react'
import { fetchAPI } from '../../../services/api'
import StatsBar from './StatsBar'
import ResultsTable from './ResultsTable'

const URGENCY = {
  critical: { label: { en: 'Critical', es: 'Critico' }, bg: '#FEE2E2', color: '#DC2626' },
  high: { label: { en: 'High', es: 'Alta' }, bg: '#FEF3C7', color: '#D97706' },
  medium: { label: { en: 'Medium', es: 'Media' }, bg: '#DBEAFE', color: '#2563EB' },
  low: { label: { en: 'Low', es: 'Baja' }, bg: '#D1FAE5', color: '#059669' },
}

function UrgencyBadge({ level, lang }) {
  const u = URGENCY[level] || URGENCY.medium
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600,
      background: u.bg, color: u.color, whiteSpace: 'nowrap',
    }}>
      {u.label[lang] || level}
    </span>
  )
}

function formatDate(iso, lang) {
  if (!iso) return '--'
  return new Date(iso).toLocaleString(lang === 'es' ? 'es-ES' : 'en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export default function TicketDashboard({ automation, lang, onBack }) {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [ticketText, setTicketText] = useState('')
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
    if (!ticketText.trim() || processing) return
    setProcessing(true)
    setError(null)

    try {
      // Run the automation
      const runRes = await fetchAPI(`/automations/${automation.id}/run`, {
        method: 'POST',
        body: JSON.stringify({ input_data: { text: ticketText.trim() } }),
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

      // Poll for completion
      let attempts = 0
      const poll = async () => {
        if (attempts > 60) {
          setError(lang === 'es' ? 'Tiempo de espera agotado' : 'Timed out waiting for result')
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
          // Save result
          const output = execRes.data?.result || execRes.data?.output || {}
          await fetchAPI('/results/', {
            method: 'POST',
            body: JSON.stringify({
              automation_id: automation.id,
              execution_id: runId,
              input_data: { text: ticketText.trim() },
              output_data: output,
              result_type: 'ticket',
            }),
          })
          setTicketText('')
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

  const color = automation.color || '#6366F1'

  // Compute stats from results
  const totalProcessed = results.length
  const avgTime = results.length > 0
    ? Math.round(results.reduce((sum, r) => sum + (r.output_data?.processing_time_ms || 800), 0) / results.length)
    : 0
  const successRate = results.length > 0
    ? Math.round((results.filter(r => r.output_data?.urgency).length / results.length) * 100)
    : 0

  const stats = [
    { label: lang === 'es' ? 'Tickets procesados' : 'Tickets processed', value: totalProcessed, color: '#6366F1' },
    { label: lang === 'es' ? 'Tiempo prom.' : 'Avg time', value: avgTime ? `${avgTime}ms` : '--', color: '#F59E0B' },
    { label: lang === 'es' ? 'Tasa de exito' : 'Success rate', value: `${successRate}%`, color: '#10B981' },
    { label: lang === 'es' ? 'Criticos' : 'Critical', value: results.filter(r => r.output_data?.urgency === 'critical').length, color: '#DC2626' },
  ]

  const columns = [
    { key: 'date', label: lang === 'es' ? 'Fecha' : 'Date' },
    { key: 'urgency', label: lang === 'es' ? 'Urgencia' : 'Urgency' },
    { key: 'category', label: lang === 'es' ? 'Categoria' : 'Category' },
    { key: 'team', label: lang === 'es' ? 'Equipo asignado' : 'Assigned Team' },
    { key: 'status', label: lang === 'es' ? 'Estado' : 'Status' },
  ]

  const renderCell = (row, key) => {
    const out = row.output_data || {}
    switch (key) {
      case 'date': return formatDate(row.created_at, lang)
      case 'urgency': return <UrgencyBadge level={out.urgency || 'medium'} lang={lang} />
      case 'category': return out.category || '--'
      case 'team': return out.assigned_team || out.team || '--'
      case 'status': return (
        <span style={{
          padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 500,
          background: out.auto_resolved ? '#D1FAE5' : '#DBEAFE',
          color: out.auto_resolved ? '#059669' : '#2563EB',
        }}>
          {out.auto_resolved
            ? (lang === 'es' ? 'Auto-resuelto' : 'Auto-resolved')
            : (lang === 'es' ? 'Asignado' : 'Assigned')}
        </span>
      )
      default: return '--'
    }
  }

  // Detail modal
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
              {lang === 'es' ? 'Analisis del Ticket' : 'Ticket Analysis'}
            </h3>
            <UrgencyBadge level={out.urgency || 'medium'} lang={lang} />
          </div>

          <div style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase' }}>
              {lang === 'es' ? 'Texto original' : 'Original text'}
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
                {lang === 'es' ? 'Categoria' : 'Category'}
              </p>
              <p style={{ fontSize: 14, color: '#374151', margin: 0 }}>{out.category || '--'}</p>
            </div>
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase' }}>
                {lang === 'es' ? 'Equipo asignado' : 'Assigned Team'}
              </p>
              <p style={{ fontSize: 14, color: '#374151', margin: 0 }}>{out.assigned_team || out.team || '--'}</p>
            </div>
          </div>

          {out.entities && out.entities.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 8, textTransform: 'uppercase' }}>
                {lang === 'es' ? 'Entidades extraidas' : 'Extracted entities'}
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {out.entities.map((e, i) => (
                  <span key={i} style={{
                    padding: '3px 10px', borderRadius: 6, fontSize: 12,
                    background: '#EEF2FF', color: '#4338CA', fontWeight: 500,
                  }}>
                    {typeof e === 'string' ? e : `${e.type}: ${e.value}`}
                  </span>
                ))}
              </div>
            </div>
          )}

          {out.auto_response && (
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase' }}>
                {lang === 'es' ? 'Respuesta auto-generada' : 'Auto-generated response'}
              </p>
              <div style={{
                padding: 12, background: '#F0FDF4', borderRadius: 8,
                border: '1px solid #BBF7D0', fontSize: 13, color: '#166534',
                lineHeight: 1.6, whiteSpace: 'pre-wrap',
              }}>
                {out.auto_response}
              </div>
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
          {automation.icon || '🎫'}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: '#111827', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {automation.name}
          </h1>
          <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0 }}>
            {lang === 'es' ? 'Triaje inteligente de tickets' : 'Intelligent ticket triage'}
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
          {lang === 'es' ? 'Procesar nuevo ticket' : 'Process new ticket'}
        </h3>
        <textarea
          value={ticketText}
          onChange={e => setTicketText(e.target.value)}
          placeholder={lang === 'es'
            ? 'Pega el texto del ticket aqui...\n\nEj: "Mi servidor de produccion esta caido desde las 3am. Clientes no pueden acceder al portal. Error 503 en todos los endpoints."'
            : 'Paste ticket text here...\n\nE.g.: "Production server has been down since 3am. Customers cannot access the portal. Error 503 on all endpoints."'}
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
            disabled={!ticketText.trim() || processing}
            style={{
              padding: '9px 20px', borderRadius: 8, border: 'none',
              fontSize: 13, fontWeight: 600, color: '#fff',
              background: (!ticketText.trim() || processing) ? '#A5B4FC' : `linear-gradient(135deg, ${color}, #8B5CF6)`,
              cursor: (!ticketText.trim() || processing) ? 'default' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            {processing && (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ animation: 'spin 1s linear infinite' }}>
                <path d="M21 12a9 9 0 11-6.219-8.56" />
              </svg>
            )}
            {processing
              ? (lang === 'es' ? 'Procesando...' : 'Processing...')
              : (lang === 'es' ? 'Procesar' : 'Process')}
          </button>
        </div>
      </div>

      {/* Results */}
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: '0 0 12px' }}>
          {lang === 'es' ? 'Tickets procesados' : 'Processed tickets'}
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
          {lang === 'es' ? 'Cargando resultados...' : 'Loading results...'}
        </div>
      ) : (
        <ResultsTable
          results={results}
          columns={columns}
          lang={lang}
          onRowClick={setSelectedResult}
          renderCell={renderCell}
          emptyIcon="🎫"
          emptyTitle={lang === 'es' ? 'Sin tickets procesados' : 'No tickets processed'}
          emptyDescription={lang === 'es'
            ? 'Pega el texto de un ticket arriba para comenzar el triaje automatico.'
            : 'Paste ticket text above to start automatic triage.'}
        />
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } } @keyframes fadeIn { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none } }`}</style>
    </div>
  )
}
