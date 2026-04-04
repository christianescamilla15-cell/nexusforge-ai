import { useState, useEffect, useCallback } from 'react'
import { fetchAPI } from '../../../services/api'
import StatsBar from './StatsBar'

function formatDate(iso, lang) {
  if (!iso) return '--'
  return new Date(iso).toLocaleString(lang === 'es' ? 'es-ES' : 'en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

const PERIODS = [
  { value: 'week', en: 'Last week', es: 'Ultima semana' },
  { value: 'month', en: 'Last month', es: 'Ultimo mes' },
  { value: 'quarter', en: 'Last quarter', es: 'Ultimo trimestre' },
]

const SOURCES = [
  { value: 'database', en: 'Database', es: 'Base de datos' },
  { value: 'api', en: 'External APIs', es: 'APIs externas' },
  { value: 'logs', en: 'System logs', es: 'Logs del sistema' },
  { value: 'metrics', en: 'Metrics', es: 'Metricas' },
]

// Simple Markdown renderer for reports
function RenderMarkdown({ text }) {
  if (!text) return null
  const lines = text.split('\n')
  return (
    <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.8 }}>
      {lines.map((line, i) => {
        if (line.startsWith('### ')) {
          return <h4 key={i} style={{ fontSize: 14, fontWeight: 700, color: '#111827', margin: '16px 0 6px' }}>{line.slice(4)}</h4>
        }
        if (line.startsWith('## ')) {
          return <h3 key={i} style={{ fontSize: 16, fontWeight: 700, color: '#111827', margin: '20px 0 8px' }}>{line.slice(3)}</h3>
        }
        if (line.startsWith('# ')) {
          return <h2 key={i} style={{ fontSize: 18, fontWeight: 700, color: '#111827', margin: '24px 0 10px' }}>{line.slice(2)}</h2>
        }
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return <div key={i} style={{ paddingLeft: 16, position: 'relative' }}>
            <span style={{ position: 'absolute', left: 4 }}>•</span>
            {line.slice(2)}
          </div>
        }
        if (line.startsWith('> ')) {
          return <blockquote key={i} style={{ borderLeft: '3px solid #8B5CF6', paddingLeft: 12, margin: '8px 0', color: '#6B7280', fontStyle: 'italic' }}>
            {line.slice(2)}
          </blockquote>
        }
        if (line.trim() === '') return <br key={i} />
        // Bold text
        const boldParsed = line.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
        return <p key={i} style={{ margin: '4px 0' }} dangerouslySetInnerHTML={{ __html: boldParsed }} />
      })}
    </div>
  )
}

export default function ReportDashboard({ automation, lang, onBack }) {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [selectedResult, setSelectedResult] = useState(null)
  const [error, setError] = useState(null)
  const [isMobile, setIsMobile] = useState(false)

  // Config form
  const [topic, setTopic] = useState('')
  const [period, setPeriod] = useState('month')
  const [selectedSources, setSelectedSources] = useState(['database', 'metrics'])

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

  const toggleSource = (src) => {
    setSelectedSources(prev =>
      prev.includes(src)
        ? prev.filter(s => s !== src)
        : [...prev, src]
    )
  }

  const handleGenerate = async () => {
    if (!topic.trim() || processing) return
    setProcessing(true)
    setError(null)

    try {
      const runRes = await fetchAPI(`/automations/${automation.id}/run`, {
        method: 'POST',
        body: JSON.stringify({
          input_data: {
            topic: topic.trim(),
            period,
            sources: selectedSources,
          },
        }),
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
        if (attempts > 90) {
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
              input_data: { topic: topic.trim(), period, sources: selectedSources },
              output_data: output,
              result_type: 'report',
            }),
          })
          setTopic('')
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

  const handleDownload = (result) => {
    const content = result.output_data?.content || result.output_data?.report || ''
    const topic = result.input_data?.topic || 'report'
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${topic.replace(/[^a-zA-Z0-9]/g, '_')}_report.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const color = automation.color || '#F59E0B'
  const totalReports = results.length
  const lastReport = results.length > 0 ? results[0].created_at : null

  const stats = [
    { label: lang === 'es' ? 'Reportes generados' : 'Reports generated', value: totalReports, color: '#F59E0B' },
    { label: lang === 'es' ? 'Ultimo reporte' : 'Last report', value: lastReport ? formatDate(lastReport, lang) : '--', color: '#6366F1' },
    { label: lang === 'es' ? 'Paginas totales' : 'Total pages', value: results.reduce((s, r) => s + (r.output_data?.pages || 1), 0), color: '#10B981' },
    { label: lang === 'es' ? 'Fuentes usadas' : 'Sources used', value: [...new Set(results.flatMap(r => r.input_data?.sources || []))].length, color: '#8B5CF6' },
  ]

  // Detail view
  if (selectedResult) {
    const out = selectedResult.output_data || {}
    const inp = selectedResult.input_data || {}
    return (
      <div style={{ animation: 'fadeIn 0.2s ease-out' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
          <button onClick={() => setSelectedResult(null)} style={{
            background: '#F3F4F6', border: 'none', borderRadius: 8,
            padding: '8px 16px', cursor: 'pointer', fontSize: 13,
            color: '#6B7280', display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span>←</span> {lang === 'es' ? 'Volver' : 'Back'}
          </button>
          <button onClick={() => handleDownload(selectedResult)} style={{
            padding: '8px 16px', borderRadius: 8, border: '1px solid #E5E7EB',
            background: '#fff', fontSize: 13, color: '#374151', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span>↓</span> {lang === 'es' ? 'Descargar .md' : 'Download .md'}
          </button>
        </div>

        <div style={{
          background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
          padding: 24,
        }}>
          <div style={{ marginBottom: 16, paddingBottom: 16, borderBottom: '1px solid #E5E7EB' }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: '#111827', margin: '0 0 6px' }}>
              {inp.topic || (lang === 'es' ? 'Reporte' : 'Report')}
            </h3>
            <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#9CA3AF', flexWrap: 'wrap' }}>
              <span>{formatDate(selectedResult.created_at, lang)}</span>
              {inp.period && <span>·  {PERIODS.find(p => p.value === inp.period)?.[lang] || inp.period}</span>}
              {out.pages && <span>· {out.pages} {lang === 'es' ? 'paginas' : 'pages'}</span>}
            </div>
          </div>

          <RenderMarkdown text={out.content || out.report || (lang === 'es' ? 'Sin contenido' : 'No content')} />
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
          {automation.icon || '📊'}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: '#111827', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {automation.name}
          </h1>
          <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0 }}>
            {lang === 'es' ? 'Generador inteligente de reportes' : 'Intelligent report generator'}
          </p>
        </div>
      </div>

      <StatsBar stats={stats} lang={lang} />

      {/* Config Form */}
      <div style={{
        background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
        padding: isMobile ? 16 : 20, marginBottom: 24,
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: '0 0 16px' }}>
          {lang === 'es' ? 'Generar nuevo reporte' : 'Generate new report'}
        </h3>

        <div style={{ marginBottom: 14 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
            {lang === 'es' ? 'Tema del reporte' : 'Report topic'}
          </label>
          <input
            value={topic}
            onChange={e => setTopic(e.target.value)}
            placeholder={lang === 'es'
              ? 'Ej: Analisis de rendimiento del sistema, Metricas de uso, etc.'
              : 'E.g.: System performance analysis, Usage metrics, etc.'}
            style={{
              width: '100%', padding: '10px 12px', borderRadius: 8,
              border: '1px solid #E5E7EB', fontSize: 13, color: '#374151',
              boxSizing: 'border-box', outline: 'none',
            }}
            onFocus={e => e.target.style.borderColor = color}
            onBlur={e => e.target.style.borderColor = '#E5E7EB'}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 16, marginBottom: 14 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
              {lang === 'es' ? 'Periodo' : 'Period'}
            </label>
            <select
              value={period}
              onChange={e => setPeriod(e.target.value)}
              style={{
                width: '100%', padding: '10px 12px', borderRadius: 8,
                border: '1px solid #E5E7EB', fontSize: 13, color: '#374151',
                background: '#fff', boxSizing: 'border-box', outline: 'none',
              }}
            >
              {PERIODS.map(p => (
                <option key={p.value} value={p.value}>{p[lang] || p.en}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
              {lang === 'es' ? 'Fuentes de datos' : 'Data sources'}
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {SOURCES.map(s => {
                const active = selectedSources.includes(s.value)
                return (
                  <button
                    key={s.value}
                    onClick={() => toggleSource(s.value)}
                    style={{
                      padding: '6px 12px', borderRadius: 6,
                      border: `1px solid ${active ? color : '#E5E7EB'}`,
                      background: active ? `${color}12` : '#fff',
                      color: active ? color : '#6B7280',
                      fontSize: 12, fontWeight: 500, cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >
                    {s[lang] || s.en}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {error && (
          <div style={{ marginBottom: 12, padding: '8px 12px', borderRadius: 8, background: '#FEF2F2', border: '1px solid #FECACA', fontSize: 12, color: '#DC2626' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={handleGenerate}
            disabled={!topic.trim() || processing}
            style={{
              padding: '9px 20px', borderRadius: 8, border: 'none',
              fontSize: 13, fontWeight: 600, color: '#fff',
              background: (!topic.trim() || processing) ? '#FCD34D' : `linear-gradient(135deg, ${color}, #F97316)`,
              cursor: (!topic.trim() || processing) ? 'default' : 'pointer',
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
              : (lang === 'es' ? 'Generar Reporte' : 'Generate Report')}
          </button>
        </div>
      </div>

      {/* Results */}
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: '0 0 12px' }}>
          {lang === 'es' ? 'Reportes generados' : 'Generated reports'}
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
          <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.4 }}>📊</div>
          <h4 style={{ fontSize: 15, fontWeight: 600, color: '#374151', margin: '0 0 6px' }}>
            {lang === 'es' ? 'Sin reportes generados' : 'No reports generated'}
          </h4>
          <p style={{ fontSize: 13, color: '#9CA3AF', margin: 0 }}>
            {lang === 'es'
              ? 'Configura el tema y periodo arriba para generar tu primer reporte.'
              : 'Configure topic and period above to generate your first report.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {results.map(r => {
            const inp = r.input_data || {}
            const out = r.output_data || {}
            return (
              <div
                key={r.id}
                style={{
                  background: '#fff', borderRadius: 10, border: '1px solid #E5E7EB',
                  padding: 16, display: 'flex', alignItems: 'center', gap: 14,
                  cursor: 'pointer', transition: 'border-color 0.15s',
                  flexWrap: isMobile ? 'wrap' : 'nowrap',
                }}
                onClick={() => setSelectedResult(r)}
                onMouseEnter={e => e.currentTarget.style.borderColor = color}
                onMouseLeave={e => e.currentTarget.style.borderColor = '#E5E7EB'}
              >
                <div style={{
                  width: 40, height: 40, borderRadius: 10,
                  background: `${color}12`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 18, flexShrink: 0,
                }}>
                  📊
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 13, fontWeight: 600, color: '#111827', margin: '0 0 2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {inp.topic || (lang === 'es' ? 'Reporte' : 'Report')}
                  </p>
                  <div style={{ display: 'flex', gap: 10, fontSize: 11, color: '#9CA3AF' }}>
                    <span>{formatDate(r.created_at, lang)}</span>
                    {out.pages && <span>{out.pages} {lang === 'es' ? 'pags' : 'pages'}</span>}
                    {inp.period && <span>{PERIODS.find(p => p.value === inp.period)?.[lang] || inp.period}</span>}
                  </div>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); handleDownload(r) }}
                  style={{
                    padding: '6px 12px', borderRadius: 6,
                    border: '1px solid #E5E7EB', background: '#fff',
                    fontSize: 12, color: '#6B7280', cursor: 'pointer',
                    flexShrink: 0, display: 'flex', alignItems: 'center', gap: 4,
                  }}
                >
                  <span>↓</span> {lang === 'es' ? 'Descargar' : 'Download'}
                </button>
              </div>
            )
          })}
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } } @keyframes fadeIn { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none } }`}</style>
    </div>
  )
}
