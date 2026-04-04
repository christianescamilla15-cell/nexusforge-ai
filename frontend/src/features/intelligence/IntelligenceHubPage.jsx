import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

const T = {
  en: {
    title: 'Intelligence Hub',
    subtitle: 'AI-powered analysis pipelines — upload documents, process enterprise operations, or run deep analysis.',
    tabEnterprise: 'Enterprise Ops',
    tabDocIntel: 'Document Intelligence',
    tabAnalyze: 'Analyze',
    inputPlaceholder: 'Paste your text here...',
    run: 'Run Analysis',
    running: 'Processing...',
    results: 'Results',
    noResults: 'Run an analysis to see results here.',
    health: 'Health',
    agents: 'Agents',
    intents: 'Supported intents',
    examples: 'Example inputs',
    history: 'History',
  },
  es: {
    title: 'Hub de Inteligencia',
    subtitle: 'Pipelines de analisis IA — sube documentos, procesa operaciones empresariales o ejecuta analisis profundo.',
    tabEnterprise: 'Operaciones',
    tabDocIntel: 'Doc Intelligence',
    tabAnalyze: 'Analizar',
    inputPlaceholder: 'Pega tu texto aqui...',
    run: 'Ejecutar Analisis',
    running: 'Procesando...',
    results: 'Resultados',
    noResults: 'Ejecuta un analisis para ver resultados aqui.',
    health: 'Salud',
    agents: 'Agentes',
    intents: 'Intenciones soportadas',
    examples: 'Ejemplos',
    history: 'Historial',
  },
}

function EnterpriseOpsTab({ lang }) {
  const t = T[lang] || T.en
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState(null)

  useEffect(() => {
    fetchAPI('/enterprise-ops/health').then(res => {
      if (res.data) setHealth(res.data)
    })
  }, [])

  const handleRun = async () => {
    if (!text.trim()) return
    setLoading(true)
    setResult(null)
    const res = await fetchAPI('/enterprise-ops/process', {
      method: 'POST',
      body: JSON.stringify({ text, language: lang }),
    })
    setLoading(false)
    if (res.data) setResult(res.data)
  }

  return (
    <div>
      {health && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ padding: '8px 14px', borderRadius: 8, background: '#F0FDF4', fontSize: 12, color: '#166534' }}>
            {t.agents}: {health.agents?.length || 0}
          </div>
          {health.supported_intents && (
            <div style={{ padding: '8px 14px', borderRadius: 8, background: '#EFF6FF', fontSize: 12, color: '#1E40AF' }}>
              {t.intents}: {health.supported_intents?.join(', ')}
            </div>
          )}
        </div>
      )}

      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder={t.inputPlaceholder}
        rows={5}
        style={{
          width: '100%', padding: 14, borderRadius: 10, border: '1px solid #E5E7EB',
          fontSize: 14, resize: 'vertical', outline: 'none', boxSizing: 'border-box',
          marginBottom: 12,
        }}
      />

      <button onClick={handleRun} disabled={loading || !text.trim()} style={{
        padding: '10px 24px', borderRadius: 8, border: 'none', fontSize: 14, fontWeight: 600,
        background: loading ? '#A5B4FC' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
        color: '#fff', cursor: loading ? 'default' : 'pointer', marginBottom: 20,
      }}>
        {loading ? t.running : t.run}
      </button>

      {result && (
        <div style={{ background: '#F9FAFB', borderRadius: 12, padding: 20, border: '1px solid #E5E7EB' }}>
          <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: '#111827' }}>{t.results}</h4>
          {result.steps && result.steps.map((step, i) => (
            <div key={i} style={{ marginBottom: 12, padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #F3F4F6' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#6366F1', marginBottom: 4 }}>
                {step.agent || step.step_name || `Step ${i + 1}`}
              </div>
              <pre style={{ fontSize: 12, color: '#374151', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {typeof step.output === 'object' ? JSON.stringify(step.output, null, 2) : String(step.output || step.result || '')}
              </pre>
            </div>
          ))}
          {result.summary && (
            <div style={{ padding: 12, background: '#EFF6FF', borderRadius: 8, fontSize: 13, color: '#1E40AF' }}>
              <strong>Summary:</strong> {result.summary}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DocIntelTab({ lang }) {
  const t = T[lang] || T.en
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [examples, setExamples] = useState([])

  useEffect(() => {
    fetchAPI('/document-intelligence/examples').then(res => {
      if (res.data?.examples || res.data?.documents) setExamples(res.data.examples || res.data.documents || [])
    })
  }, [])

  const handleRun = async () => {
    if (!text.trim()) return
    setLoading(true)
    setResult(null)
    const res = await fetchAPI('/document-intelligence/run', {
      method: 'POST',
      body: JSON.stringify({ text, language: lang }),
    })
    setLoading(false)
    if (res.data) setResult(res.data)
  }

  return (
    <div>
      {examples.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 8 }}>{t.examples}:</p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {examples.slice(0, 3).map((ex, i) => (
              <button key={i} onClick={() => setText(ex.text || ex.content || JSON.stringify(ex))}
                style={{
                  padding: '6px 12px', borderRadius: 6, border: '1px solid #E5E7EB',
                  background: '#fff', fontSize: 12, cursor: 'pointer', color: '#374151',
                }}>
                {ex.title || ex.name || `Example ${i + 1}`}
              </button>
            ))}
          </div>
        </div>
      )}

      <textarea value={text} onChange={e => setText(e.target.value)}
        placeholder={t.inputPlaceholder} rows={5}
        style={{
          width: '100%', padding: 14, borderRadius: 10, border: '1px solid #E5E7EB',
          fontSize: 14, resize: 'vertical', outline: 'none', boxSizing: 'border-box', marginBottom: 12,
        }}
      />

      <button onClick={handleRun} disabled={loading || !text.trim()} style={{
        padding: '10px 24px', borderRadius: 8, border: 'none', fontSize: 14, fontWeight: 600,
        background: loading ? '#A5B4FC' : 'linear-gradient(135deg, #059669, #10B981)',
        color: '#fff', cursor: loading ? 'default' : 'pointer', marginBottom: 20,
      }}>
        {loading ? t.running : t.run}
      </button>

      {result && (
        <div style={{ background: '#F9FAFB', borderRadius: 12, padding: 20, border: '1px solid #E5E7EB' }}>
          <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: '#111827' }}>{t.results}</h4>
          {result.steps && result.steps.map((step, i) => (
            <div key={i} style={{ marginBottom: 12, padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #F3F4F6' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#059669', marginBottom: 4 }}>
                {step.agent || step.step_name || `Step ${i + 1}`}
              </div>
              <pre style={{ fontSize: 12, color: '#374151', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {typeof step.output === 'object' ? JSON.stringify(step.output, null, 2) : String(step.output || '')}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function AnalyzeTab({ lang }) {
  const t = T[lang] || T.en
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])

  useEffect(() => {
    fetchAPI('/pipeline-runs?limit=5').then(res => {
      if (res.data?.runs) setHistory(res.data.runs)
      else if (Array.isArray(res.data)) setHistory(res.data.slice(0, 5))
    })
  }, [])

  const handleRun = async () => {
    if (!text.trim()) return
    setLoading(true)
    setResult(null)
    const res = await fetchAPI('/analyze/text', {
      method: 'POST',
      body: JSON.stringify({ text, language: lang }),
    })
    setLoading(false)
    if (res.data) setResult(res.data)
  }

  return (
    <div>
      <textarea value={text} onChange={e => setText(e.target.value)}
        placeholder={t.inputPlaceholder} rows={5}
        style={{
          width: '100%', padding: 14, borderRadius: 10, border: '1px solid #E5E7EB',
          fontSize: 14, resize: 'vertical', outline: 'none', boxSizing: 'border-box', marginBottom: 12,
        }}
      />

      <button onClick={handleRun} disabled={loading || !text.trim()} style={{
        padding: '10px 24px', borderRadius: 8, border: 'none', fontSize: 14, fontWeight: 600,
        background: loading ? '#A5B4FC' : 'linear-gradient(135deg, #D97706, #F59E0B)',
        color: '#fff', cursor: loading ? 'default' : 'pointer', marginBottom: 20,
      }}>
        {loading ? t.running : t.run}
      </button>

      {result && (
        <div style={{ background: '#F9FAFB', borderRadius: 12, padding: 20, border: '1px solid #E5E7EB', marginBottom: 20 }}>
          <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: '#111827' }}>{t.results}</h4>
          <pre style={{ fontSize: 12, color: '#374151', whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0 }}>
            {typeof result === 'object' ? JSON.stringify(result, null, 2) : String(result)}
          </pre>
        </div>
      )}

      {history.length > 0 && (
        <div>
          <h4 style={{ fontSize: 13, fontWeight: 600, color: '#9CA3AF', marginBottom: 8 }}>{t.history}</h4>
          {history.map((run, i) => (
            <div key={i} style={{
              padding: '8px 12px', borderRadius: 8, background: '#fff', border: '1px solid #F3F4F6',
              marginBottom: 6, fontSize: 12, display: 'flex', justifyContent: 'space-between',
            }}>
              <span style={{ color: '#374151' }}>{run.pipeline_name || run.name || `Run ${i + 1}`}</span>
              <span style={{ color: '#9CA3AF' }}>{run.created_at ? new Date(run.created_at).toLocaleDateString() : ''}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function IntelligenceHubPage({ lang = 'en' }) {
  const t = T[lang] || T.en
  const [tab, setTab] = useState('enterprise')
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const tabs = [
    { key: 'enterprise', label: t.tabEnterprise, color: '#6366F1' },
    { key: 'docIntel', label: t.tabDocIntel, color: '#059669' },
    { key: 'analyze', label: t.tabAnalyze, color: '#D97706' },
  ]

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          {t.title}
        </h1>
        <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>{t.subtitle}</p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24, background: '#F3F4F6', borderRadius: 10, padding: 4 }}>
        {tabs.map(tb => (
          <button key={tb.key} onClick={() => setTab(tb.key)} style={{
            flex: 1, padding: '10px 16px', borderRadius: 8, border: 'none',
            fontSize: 13, fontWeight: 600, cursor: 'pointer',
            background: tab === tb.key ? '#fff' : 'transparent',
            color: tab === tb.key ? tb.color : '#6B7280',
            boxShadow: tab === tb.key ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
            transition: 'all 0.2s',
          }}>
            {tb.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #E5E7EB', padding: isMobile ? 16 : 24 }}>
        {tab === 'enterprise' && <EnterpriseOpsTab lang={lang} />}
        {tab === 'docIntel' && <DocIntelTab lang={lang} />}
        {tab === 'analyze' && <AnalyzeTab lang={lang} />}
      </div>
    </div>
  )
}
