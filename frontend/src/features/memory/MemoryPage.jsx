import { useState, useEffect, useRef, useCallback } from 'react'
import { t } from '../../shared/i18n/translations'

const AGENTS_LIST = [
  'DocClassifier', 'EntityExtractor', 'SummaryAgent', 'ContentGen', 'FlowRouter',
  'DataValidator', 'PriorityRanker', 'SchemaValidator',
]

const INITIAL_WORKING = [
  { id: 'w1', text: 'Clasificar doc_47.pdf como legal', agent: 'DocClassifier', ts: Date.now() - 45000, status: 'active' },
  { id: 'w2', text: 'Paso actual: extraer entidades de contrato', agent: 'EntityExtractor', ts: Date.now() - 30000, status: 'active' },
  { id: 'w3', text: 'Context tokens: 1247 / 4096', agent: 'FlowRouter', ts: Date.now() - 20000, status: 'active' },
  { id: 'w4', text: 'Validando schema de salida JSON', agent: 'DataValidator', ts: Date.now() - 12000, status: 'active' },
  { id: 'w5', text: 'Generando resumen ejecutivo #89', agent: 'SummaryAgent', ts: Date.now() - 5000, status: 'active' },
]

const INITIAL_EPISODIC = [
  { id: 'e1', text: 'Run-2024-Q4: clasificacion exitosa de 342 docs', agent: 'DocClassifier', type: 'success', ttlPct: 87 },
  { id: 'e2', text: 'Timeout en paso 2 resuelto con retry', agent: 'EntityExtractor', type: 'error_resolved', ttlPct: 72 },
  { id: 'e3', text: 'Patron detectado: contratos > 20pp necesitan chunking', agent: 'SummaryAgent', type: 'pattern', ttlPct: 65 },
  { id: 'e4', text: 'Rendimiento promedio: 0.94 en ultimas 127 ejecuciones', agent: 'FlowRouter', type: 'metric', ttlPct: 54 },
  { id: 'e5', text: 'Agente escalado a claude-opus por complejidad', agent: 'ContentGen', type: 'escalation', ttlPct: 41 },
]

const INITIAL_SEMANTIC = [
  { id: 's1', text: 'Documentos legales tienen patron de entidades: partes, fechas, clausulas', agent: 'DocClassifier', sim: 0.94, vector: [0.8, 0.3, 0.6, 0.9, 0.2, 0.7, 0.4, 0.85] },
  { id: 's2', text: 'Contratos financieros requieren extraccion de montos con 2 decimales', agent: 'EntityExtractor', sim: 0.91, vector: [0.5, 0.9, 0.3, 0.7, 0.8, 0.2, 0.6, 0.45] },
  { id: 's3', text: 'Resumenes optimos: 3-5 bullet points para docs < 10pp', agent: 'SummaryAgent', sim: 0.88, vector: [0.7, 0.4, 0.8, 0.5, 0.3, 0.9, 0.55, 0.6] },
  { id: 's4', text: 'Regla: priorizar velocidad sobre precision en clasificacion inicial', agent: 'FlowRouter', sim: 0.85, vector: [0.3, 0.7, 0.5, 0.4, 0.9, 0.6, 0.8, 0.35] },
  { id: 's5', text: 'Schema JSON v3: campos obligatorios [id, type, confidence, entities]', agent: 'DataValidator', sim: 0.82, vector: [0.6, 0.5, 0.9, 0.3, 0.4, 0.8, 0.7, 0.5] },
]

let idCounter = 100

function timeAgo(ts) {
  const s = Math.floor((Date.now() - ts) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  return `${Math.floor(s / 3600)}h ago`
}

export default function MemoryPage({ lang = 'en' }) {
  const [working, setWorking] = useState(INITIAL_WORKING)
  const [episodic, setEpisodic] = useState(INITIAL_EPISODIC)
  const [semantic, setSemantic] = useState(INITIAL_SEMANTIC)
  const [input, setInput] = useState('')
  const [selectedAgent, setSelectedAgent] = useState(AGENTS_LIST[0])
  const [searchQuery, setSearchQuery] = useState('')
  const [crossAgent, setCrossAgent] = useState(false)
  const [animatingToEpisodic, setAnimatingToEpisodic] = useState(null)
  const [animatingToSemantic, setAnimatingToSemantic] = useState(null)
  const [shimmer, setShimmer] = useState(null)
  const [isMobile, setIsMobile] = useState(false)
  const [flowPulse, setFlowPulse] = useState({ we: false, es: false, sw: false })
  const inputRef = useRef(null)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 900)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const handleStore = useCallback(() => {
    if (!input.trim()) return
    const id = `user-${++idCounter}`
    const newItem = { id, text: input.trim(), agent: selectedAgent, ts: Date.now(), status: 'active' }

    // Add to working memory immediately
    setWorking(prev => {
      const next = [newItem, ...prev]
      return next.slice(0, 5)
    })

    setInput('')
    inputRef.current?.focus()

    // After 2s: animate to episodic
    setTimeout(() => {
      setAnimatingToEpisodic(id)
      setFlowPulse(p => ({ ...p, we: true }))
      setTimeout(() => {
        setAnimatingToEpisodic(null)
        setFlowPulse(p => ({ ...p, we: false }))
        const epiItem = { id: `epi-${id}`, text: newItem.text, agent: selectedAgent, type: 'new_entry', ttlPct: 100 }
        setEpisodic(prev => [epiItem, ...prev].slice(0, 8))
      }, 800)
    }, 2000)

    // After 3s: shimmer + add to semantic
    setTimeout(() => {
      setShimmer(`epi-${id}`)
      setFlowPulse(p => ({ ...p, es: true }))
      setTimeout(() => {
        setShimmer(null)
        setAnimatingToSemantic(`epi-${id}`)
        setTimeout(() => {
          setAnimatingToSemantic(null)
          setFlowPulse(p => ({ ...p, es: false }))
          const randVec = Array.from({ length: 8 }, () => +(Math.random()).toFixed(2))
          const semItem = { id: `sem-${id}`, text: newItem.text, agent: selectedAgent, sim: +(0.75 + Math.random() * 0.2).toFixed(2), vector: randVec }
          setSemantic(prev => [semItem, ...prev].slice(0, 8))
        }, 800)
      }, 600)
    }, 3000)
  }, [input, selectedAgent])

  const handleSearch = useCallback((q) => {
    setSearchQuery(q)
    if (q.trim()) {
      setFlowPulse(p => ({ ...p, sw: true }))
      setTimeout(() => setFlowPulse(p => ({ ...p, sw: false })), 1500)
    }
  }, [])

  const filteredSemantic = searchQuery.trim()
    ? semantic.filter(s => {
        const match = s.text.toLowerCase().includes(searchQuery.toLowerCase())
        if (!crossAgent) return match && s.agent === selectedAgent
        return match
      }).map(s => ({ ...s, highlighted: true, matchScore: +(0.7 + Math.random() * 0.28).toFixed(2) }))
    : semantic

  const columnStyle = (color, borderColor) => ({
    flex: 1,
    minWidth: isMobile ? '100%' : 300,
    background: '#161E2E',
    border: `1px solid ${borderColor}`,
    borderRadius: 14,
    padding: 18,
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    transition: 'all 0.3s',
  })

  const cardStyle = (bg, border, isAnimating) => ({
    background: bg,
    border: `1px solid ${border}`,
    borderRadius: 10,
    padding: '10px 14px',
    fontSize: 12,
    transition: 'all 0.4s ease',
    opacity: isAnimating ? 0 : 1,
    transform: isAnimating ? 'translateX(40px) scale(0.9)' : 'translateX(0) scale(1)',
  })

  const badgeStyle = (bg, color) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '2px 8px',
    borderRadius: 6,
    background: bg,
    color,
    fontSize: 10,
    fontWeight: 600,
    whiteSpace: 'nowrap',
  })

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 4 }}>
          {t('memorySystem', lang)}
        </h1>
        <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
          {lang === 'es'
            ? 'Sistema de memoria de 3 niveles. Escribe algo para ver como fluye entre Working, Episodic y Semantic.'
            : '3-tier memory system. Type something to watch it flow through Working, Episodic, and Semantic memory.'
          }
        </p>
      </div>

      {/* Input section */}
      <div data-tour="memory-input" style={{
        background: '#161E2E', borderRadius: 12, padding: 16, marginBottom: 20,
        border: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center',
      }}>
        <select
          value={selectedAgent}
          onChange={(e) => setSelectedAgent(e.target.value)}
          aria-label={lang === 'es' ? 'Seleccionar agente' : 'Select agent'}
          style={{
            padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)',
            background: '#0A0B0F', color: '#E5E7EB', fontSize: 13, outline: 'none',
            minWidth: 150,
          }}
        >
          {AGENTS_LIST.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleStore()}
          placeholder={t('storeMemory', lang)}
          aria-label={t('storeMemory', lang)}
          style={{
            flex: 1, minWidth: 200, padding: '8px 14px', borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.1)', background: '#0A0B0F',
            color: '#E5E7EB', fontSize: 13, outline: 'none',
          }}
          onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.5)'}
          onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
        />
        <button
          onClick={handleStore}
          aria-label={lang === 'es' ? 'Almacenar memoria' : 'Store memory'}
          style={{
            padding: '8px 20px', borderRadius: 8, border: 'none',
            background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
            color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.03)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
        >
          {lang === 'es' ? 'Almacenar' : 'Store'}
        </button>
      </div>

      {/* Search section */}
      <div style={{
        background: '#161E2E', borderRadius: 12, padding: 16, marginBottom: 20,
        border: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center',
      }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
        </svg>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder={t('searchMemories', lang)}
          aria-label={t('searchMemories', lang)}
          style={{
            flex: 1, minWidth: 200, padding: '8px 14px', borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.1)', background: '#0A0B0F',
            color: '#E5E7EB', fontSize: 13, outline: 'none',
          }}
        />
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12, color: '#9CA3AF' }}>
          <div
            onClick={() => setCrossAgent(!crossAgent)}
            role="switch"
            aria-checked={crossAgent}
            aria-label={t('crossAgentSharing', lang)}
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && setCrossAgent(!crossAgent)}
            style={{
              width: 36, height: 20, borderRadius: 10, position: 'relative', cursor: 'pointer',
              background: crossAgent ? 'rgba(99,102,241,0.4)' : 'rgba(255,255,255,0.1)',
              transition: 'background 0.2s',
            }}
          >
            <div style={{
              width: 16, height: 16, borderRadius: '50%', position: 'absolute', top: 2,
              left: crossAgent ? 18 : 2,
              background: crossAgent ? '#818CF8' : '#6B7280',
              transition: 'left 0.2s',
            }} />
          </div>
          {t('crossAgentSharing', lang)}
        </label>
      </div>

      {/* Flow visualization - arrows between columns (desktop only) */}
      {!isMobile && (
        <div style={{
          display: 'flex', justifyContent: 'center', gap: 0, marginBottom: 8,
          alignItems: 'center', padding: '0 60px',
        }}>
          <div style={{ flex: 1, textAlign: 'center' }}>
            <span style={{
              ...badgeStyle('rgba(59,130,246,0.15)', '#60A5FA'),
              fontSize: 11,
            }}>{t('workingMemory', lang)}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0 8px' }}>
            <svg width="80" height="24" viewBox="0 0 80 24" aria-hidden="true">
              <defs>
                <linearGradient id="arrow-we">
                  <stop offset="0%" stopColor="#3B82F6" />
                  <stop offset="100%" stopColor="#F59E0B" />
                </linearGradient>
              </defs>
              <line x1="4" y1="12" x2="68" y2="12" stroke={flowPulse.we ? 'url(#arrow-we)' : '#4B5563'} strokeWidth={flowPulse.we ? 2.5 : 1.5} strokeDasharray={flowPulse.we ? 'none' : '4 3'}>
                {flowPulse.we && <animate attributeName="stroke-dashoffset" from="20" to="0" dur="0.5s" repeatCount="indefinite" />}
              </line>
              <polygon points="70,6 80,12 70,18" fill={flowPulse.we ? '#F59E0B' : '#4B5563'} />
            </svg>
            <span style={{ fontSize: 9, color: flowPulse.we ? '#F59E0B' : '#6B7280', whiteSpace: 'nowrap' }}>Task summary</span>
          </div>
          <div style={{ flex: 1, textAlign: 'center' }}>
            <span style={{
              ...badgeStyle('rgba(245,158,11,0.15)', '#F59E0B'),
              fontSize: 11,
            }}>{t('episodicMemory', lang)}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0 8px' }}>
            <svg width="80" height="24" viewBox="0 0 80 24" aria-hidden="true">
              <defs>
                <linearGradient id="arrow-es">
                  <stop offset="0%" stopColor="#F59E0B" />
                  <stop offset="100%" stopColor="#10B981" />
                </linearGradient>
              </defs>
              <line x1="4" y1="12" x2="68" y2="12" stroke={flowPulse.es ? 'url(#arrow-es)' : '#4B5563'} strokeWidth={flowPulse.es ? 2.5 : 1.5} strokeDasharray={flowPulse.es ? 'none' : '4 3'}>
                {flowPulse.es && <animate attributeName="stroke-dashoffset" from="20" to="0" dur="0.5s" repeatCount="indefinite" />}
              </line>
              <polygon points="70,6 80,12 70,18" fill={flowPulse.es ? '#10B981' : '#4B5563'} />
            </svg>
            <span style={{ fontSize: 9, color: flowPulse.es ? '#10B981' : '#6B7280', whiteSpace: 'nowrap' }}>Embed + persist</span>
          </div>
          <div style={{ flex: 1, textAlign: 'center' }}>
            <span style={{
              ...badgeStyle('rgba(16,185,129,0.15)', '#10B981'),
              fontSize: 11,
            }}>{t('semanticMemory', lang)}</span>
          </div>
        </div>
      )}

      {/* Recall arrow (search active) */}
      {!isMobile && searchQuery.trim() && (
        <div style={{
          display: 'flex', justifyContent: 'center', marginBottom: 8, alignItems: 'center', padding: '0 60px',
        }}>
          <div style={{ flex: 1 }} />
          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <svg width="200" height="24" viewBox="0 0 200 24" aria-hidden="true">
              <defs>
                <linearGradient id="arrow-sw">
                  <stop offset="0%" stopColor="#10B981" />
                  <stop offset="100%" stopColor="#3B82F6" />
                </linearGradient>
              </defs>
              <line x1="196" y1="12" x2="12" y2="12" stroke={flowPulse.sw ? 'url(#arrow-sw)' : '#4B5563'} strokeWidth={flowPulse.sw ? 2.5 : 1.5} strokeDasharray={flowPulse.sw ? 'none' : '4 3'} />
              <polygon points="12,6 2,12 12,18" fill={flowPulse.sw ? '#3B82F6' : '#4B5563'} />
            </svg>
            <span style={{ fontSize: 9, color: flowPulse.sw ? '#3B82F6' : '#6B7280', whiteSpace: 'nowrap' }}>Recall similar</span>
          </div>
        </div>
      )}

      {/* 3 columns */}
      <div style={{
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        gap: 16,
      }}>
        {/* Working Memory */}
        <div style={columnStyle('#3B82F6', 'rgba(59,130,246,0.25)')}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M12 6v6l4 2" /><circle cx="12" cy="12" r="10" />
              </svg>
              <span style={{ fontSize: 14, fontWeight: 600, color: '#60A5FA' }}>{t('workingMemory', lang)}</span>
            </div>
            <span style={badgeStyle('rgba(59,130,246,0.15)', '#60A5FA')}>{t('inProcess', lang)}</span>
          </div>
          <div style={{ fontSize: 10, color: '#6B7280', marginBottom: 6 }}>
            {lang === 'es' ? 'Se reinicia al terminar la ejecucion' : 'Resets on execution end'} | Max 5
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
            {working.map((item) => (
              <div
                key={item.id}
                aria-label={`Working memory: ${item.text}`}
                style={cardStyle(
                  'rgba(59,130,246,0.08)',
                  animatingToEpisodic === item.id ? 'rgba(245,158,11,0.4)' : 'rgba(59,130,246,0.15)',
                  animatingToEpisodic === item.id
                )}
              >
                <div style={{ color: '#E5E7EB', marginBottom: 4, lineHeight: 1.4 }}>{item.text}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#6B7280', fontSize: 10 }}>{item.agent} | {timeAgo(item.ts)}</span>
                  <span style={badgeStyle('rgba(59,130,246,0.2)', '#60A5FA')}>Active</span>
                </div>
              </div>
            ))}
            {working.length === 0 && (
              <div style={{ color: '#4B5563', fontSize: 12, textAlign: 'center', padding: 20 }}>
                {lang === 'es' ? 'Vacio — escribe algo arriba' : 'Empty — type something above'}
              </div>
            )}
          </div>
        </div>

        {/* Episodic Memory */}
        <div style={columnStyle('#F59E0B', 'rgba(245,158,11,0.25)')}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span style={{ fontSize: 14, fontWeight: 600, color: '#FBBF24' }}>{t('episodicMemory', lang)}</span>
            </div>
            <span style={badgeStyle('rgba(245,158,11,0.15)', '#FBBF24')}>{t('ttl30Days', lang)}</span>
          </div>
          <div style={{ fontSize: 10, color: '#6B7280', marginBottom: 6 }}>
            Redis | {lang === 'es' ? 'Historial de episodios' : 'Episode history'}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
            {episodic.map((item) => (
              <div
                key={item.id}
                aria-label={`Episodic memory: ${item.text}`}
                style={{
                  ...cardStyle(
                    shimmer === item.id ? 'rgba(245,158,11,0.2)' : 'rgba(245,158,11,0.08)',
                    animatingToSemantic === item.id ? 'rgba(16,185,129,0.4)' : 'rgba(245,158,11,0.15)',
                    animatingToSemantic === item.id
                  ),
                  ...(shimmer === item.id ? {
                    backgroundImage: 'linear-gradient(90deg, rgba(245,158,11,0.08) 0%, rgba(245,158,11,0.25) 50%, rgba(245,158,11,0.08) 100%)',
                    backgroundSize: '200% 100%',
                    animation: 'shimmerAnim 1s ease-in-out',
                  } : {}),
                }}
              >
                <div style={{ color: '#E5E7EB', marginBottom: 4, lineHeight: 1.4 }}>{item.text}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                  <span style={{ color: '#6B7280', fontSize: 10 }}>{item.agent}</span>
                  <span style={{
                    ...badgeStyle('rgba(245,158,11,0.15)', '#FBBF24'),
                    fontSize: 9,
                  }}>{item.type}</span>
                </div>
                {/* TTL bar */}
                <div style={{ marginTop: 4 }}>
                  <div style={{
                    width: '100%', height: 3, background: 'rgba(255,255,255,0.05)',
                    borderRadius: 2, overflow: 'hidden',
                  }}>
                    <div style={{
                      width: `${item.ttlPct}%`, height: '100%', borderRadius: 2,
                      background: item.ttlPct > 50 ? '#F59E0B' : item.ttlPct > 20 ? '#F97316' : '#EF4444',
                      transition: 'width 0.5s',
                    }} />
                  </div>
                  <div style={{ fontSize: 9, color: '#6B7280', marginTop: 2 }}>TTL: {item.ttlPct}%</div>
                </div>
              </div>
            ))}
          </div>

          {/* Pattern recognition */}
          <div style={{
            marginTop: 8, padding: '8px 12px', background: 'rgba(245,158,11,0.06)',
            borderRadius: 8, border: '1px solid rgba(245,158,11,0.1)',
          }}>
            <div style={{ fontSize: 10, color: '#FBBF24', fontWeight: 600, marginBottom: 2 }}>
              {lang === 'es' ? 'Reconocimiento de patrones' : 'Pattern Recognition'}
            </div>
            <div style={{ fontSize: 11, color: '#9CA3AF' }}>
              {t('successRate', lang)}: <span style={{ color: '#10B981', fontWeight: 600 }}>78%</span>
              {' '}{lang === 'es' ? 'basado en episodios almacenados' : 'based on stored episodes'}
            </div>
          </div>
        </div>

        {/* Semantic Memory */}
        <div style={columnStyle('#10B981', 'rgba(16,185,129,0.25)')}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
              <span style={{ fontSize: 14, fontWeight: 600, color: '#34D399' }}>{t('semanticMemory', lang)}</span>
            </div>
            <span style={badgeStyle('rgba(16,185,129,0.15)', '#34D399')}>{t('permanent', lang)}</span>
          </div>
          <div style={{ fontSize: 10, color: '#6B7280', marginBottom: 6 }}>
            pgvector | {lang === 'es' ? 'Busqueda por similaridad' : 'Similarity search'}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
            {filteredSemantic.map((item) => (
              <div
                key={item.id}
                aria-label={`Semantic memory: ${item.text}`}
                style={{
                  ...cardStyle(
                    item.highlighted ? 'rgba(16,185,129,0.15)' : 'rgba(16,185,129,0.08)',
                    item.highlighted ? 'rgba(16,185,129,0.4)' : 'rgba(16,185,129,0.15)',
                    false
                  ),
                  ...(item.highlighted ? { boxShadow: '0 0 12px rgba(16,185,129,0.2)' } : {}),
                }}
              >
                <div style={{ color: '#E5E7EB', marginBottom: 4, lineHeight: 1.4 }}>{item.text}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                  <span style={{ color: '#6B7280', fontSize: 10 }}>{item.agent}</span>
                  {item.highlighted && item.matchScore && (
                    <span style={{ ...badgeStyle('rgba(99,102,241,0.2)', '#818CF8'), fontSize: 9 }}>
                      Match: {item.matchScore}
                    </span>
                  )}
                  <span style={badgeStyle('rgba(16,185,129,0.15)', '#34D399')}>512d vector</span>
                </div>
                {/* Vector heatmap */}
                <div style={{ display: 'flex', gap: 1, marginTop: 4, height: 12 }}>
                  {item.vector.map((v, i) => (
                    <div key={i} style={{
                      flex: 1, borderRadius: 1,
                      background: `rgba(16, 185, 129, ${0.15 + v * 0.7})`,
                      height: `${20 + v * 80}%`,
                      alignSelf: 'flex-end',
                      transition: 'height 0.3s',
                    }} />
                  ))}
                  <span style={{ fontSize: 8, color: '#6B7280', marginLeft: 4, alignSelf: 'center' }}>sim: {item.sim}</span>
                </div>
                {item.highlighted && crossAgent && item.agent !== selectedAgent && (
                  <div style={{ marginTop: 4, fontSize: 9, color: '#818CF8', fontStyle: 'italic' }}>
                    {lang === 'es' ? 'Transferencia de conocimiento entre agentes' : 'Cross-agent knowledge transfer'}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Shimmer animation keyframes */}
      <style>{`
        @keyframes shimmerAnim {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
