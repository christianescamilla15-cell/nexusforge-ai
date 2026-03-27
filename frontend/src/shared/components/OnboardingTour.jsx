import { useState, useEffect, useCallback } from 'react'
import { t } from '../i18n/translations'

// ─── Demo Sub-Components ────────────────────────────────────────────────────

function DemoPanel({ children, playing }) {
  return (
    <div style={{
      background: '#1A1F2E',
      border: playing
        ? '1px solid rgba(99,102,241,0.6)'
        : '1px solid rgba(99,102,241,0.25)',
      borderRadius: 12,
      padding: '16px 18px',
      marginTop: 14,
      position: 'relative',
      overflow: 'hidden',
      transition: 'border-color 0.4s ease',
      boxShadow: playing ? '0 0 20px rgba(99,102,241,0.12)' : 'none',
    }}>
      <span style={{
        position: 'absolute', top: 8, right: 10,
        fontSize: 9, fontWeight: 700, letterSpacing: '0.1em',
        color: playing ? '#818CF8' : '#4B5563',
        textTransform: 'uppercase',
        transition: 'color 0.3s',
      }}>
        DEMO
      </span>
      {children}
    </div>
  )
}

// Step 1: Dashboard KPIs animate up
function DashboardDemo({ lang }) {
  const kpis = [
    { label: 'Workflows', target: 12, color: '#6366F1' },
    { label: lang === 'es' ? 'Activos' : 'Active', target: 3, color: '#10B981' },
    { label: lang === 'es' ? 'Agentes' : 'Agents', target: 22, color: '#F59E0B' },
    { label: 'Docs', target: 47, color: '#EC4899' },
  ]
  const [vals, setVals] = useState([0, 0, 0, 0])
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    let frame = 0
    const totalFrames = 40
    const id = setInterval(() => {
      frame++
      const pct = Math.min(frame / totalFrames, 1)
      const ease = 1 - Math.pow(1 - pct, 3)
      setVals(kpis.map(k => Math.round(k.target * ease)))
      if (frame >= totalFrames) { clearInterval(id); setPlaying(false) }
    }, 40)
    return () => clearInterval(id)
  }, [])

  return (
    <DemoPanel playing={playing}>
      <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
        {kpis.map((k, i) => (
          <div key={i} style={{
            flex: 1, textAlign: 'center', padding: '10px 4px',
            background: 'rgba(255,255,255,0.03)', borderRadius: 8,
            border: `1px solid ${k.color}33`,
          }}>
            <div style={{
              fontSize: 22, fontWeight: 800, color: k.color,
              fontVariantNumeric: 'tabular-nums',
              transition: 'color 0.2s',
            }}>
              {vals[i]}
            </div>
            <div style={{ fontSize: 10, color: '#9CA3AF', marginTop: 2 }}>{k.label}</div>
          </div>
        ))}
      </div>
    </DemoPanel>
  )
}

// Step 2: Workflow DAG animation
function WorkflowDemo() {
  const nodes = ['Classify', 'Extract', 'Summarize']
  const [active, setActive] = useState(-1)
  const [arrowProgress, setArrowProgress] = useState([0, 0])
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    const timers = []
    // Arrow 1 draws, then node 0 lights
    timers.push(setTimeout(() => setActive(0), 200))
    timers.push(setTimeout(() => setArrowProgress([1, 0]), 1000))
    timers.push(setTimeout(() => setActive(1), 1400))
    timers.push(setTimeout(() => setArrowProgress([1, 1]), 2200))
    timers.push(setTimeout(() => { setActive(2); setPlaying(false) }, 2600))
    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <DemoPanel playing={playing}>
      <svg width="100%" height="60" viewBox="0 0 380 60" style={{ display: 'block' }}>
        {nodes.map((n, i) => {
          const x = 20 + i * 130
          const isActive = i <= active
          return (
            <g key={i}>
              <rect x={x} y={10} width={100} height={40} rx={8}
                fill={isActive ? '#6366F122' : '#0D1117'}
                stroke={isActive ? '#6366F1' : '#374151'}
                strokeWidth={isActive ? 2 : 1}
                style={{ transition: 'all 0.4s ease' }}
              />
              <text x={x + 50} y={35} textAnchor="middle"
                fill={isActive ? '#E5E7EB' : '#6B7280'}
                fontSize={12} fontWeight={600}
                style={{ transition: 'fill 0.3s' }}
              >
                {n}
              </text>
              {i < 2 && (
                <line
                  x1={x + 100} y1={30} x2={x + 130} y2={30}
                  stroke="#6366F1"
                  strokeWidth={2}
                  strokeDasharray="30"
                  strokeDashoffset={30 - 30 * arrowProgress[i]}
                  style={{ transition: 'stroke-dashoffset 0.6s ease' }}
                />
              )}
              {i < 2 && (
                <polygon
                  points={`${x + 127},25 ${x + 133},30 ${x + 127},35`}
                  fill="#6366F1"
                  opacity={arrowProgress[i]}
                  style={{ transition: 'opacity 0.3s' }}
                />
              )}
            </g>
          )
        })}
      </svg>
    </DemoPanel>
  )
}

// Step 3: Execution simulation
function ExecutionDemo({ lang }) {
  const steps = [
    { name: 'Classify', dur: '0.4s' },
    { name: 'Extract', dur: '0.8s' },
    { name: 'Validate', dur: '0.3s' },
    { name: 'Report', dur: '0.8s' },
  ]
  const [statuses, setStatuses] = useState(['pending', 'pending', 'pending', 'pending'])
  const [progress, setProgress] = useState(0)
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    const timers = []
    steps.forEach((_, i) => {
      timers.push(setTimeout(() => {
        setStatuses(prev => { const n = [...prev]; n[i] = 'running'; return n })
        setProgress((i) / steps.length * 100)
      }, i * 1000))
      timers.push(setTimeout(() => {
        setStatuses(prev => { const n = [...prev]; n[i] = 'completed'; return n })
        setProgress((i + 1) / steps.length * 100)
        if (i === steps.length - 1) setPlaying(false)
      }, i * 1000 + 700))
    })
    return () => timers.forEach(clearTimeout)
  }, [])

  const statusColor = { pending: '#4B5563', running: '#3B82F6', completed: '#10B981' }
  const statusIcon = { pending: '\u25CB', running: '\u25CF', completed: '\u2713' }

  return (
    <DemoPanel playing={playing}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {steps.map((s, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '6px 10px', borderRadius: 6,
            background: statuses[i] === 'running' ? 'rgba(59,130,246,0.08)' : 'transparent',
            transition: 'background 0.3s',
          }}>
            <span style={{
              fontSize: 14, color: statusColor[statuses[i]],
              animation: statuses[i] === 'running' ? 'nxfDemoPulse 1s infinite' : 'none',
              width: 16, textAlign: 'center', fontWeight: 700,
            }}>
              {statusIcon[statuses[i]]}
            </span>
            <span style={{ fontSize: 12, color: '#D1D5DB', flex: 1, fontWeight: 500 }}>{s.name}</span>
            <span style={{ fontSize: 10, color: '#6B7280' }}>{s.dur}</span>
            <span style={{
              fontSize: 10, fontWeight: 600,
              color: statusColor[statuses[i]],
              textTransform: 'capitalize',
              minWidth: 65, textAlign: 'right',
            }}>
              {statuses[i] === 'running' ? (lang === 'es' ? 'ejecutando' : 'running')
                : statuses[i] === 'completed' ? (lang === 'es' ? 'listo' : 'done') : ''}
            </span>
          </div>
        ))}
      </div>
      {/* Progress bar */}
      <div style={{
        height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)',
        overflow: 'hidden', marginTop: 10,
      }}>
        <div style={{
          height: '100%', borderRadius: 2, width: `${progress}%`,
          background: 'linear-gradient(90deg, #3B82F6, #10B981)',
          transition: 'width 0.5s ease',
        }} />
      </div>
      {progress >= 100 && (
        <div style={{
          display: 'flex', justifyContent: 'center', gap: 16, marginTop: 8,
          fontSize: 11, color: '#9CA3AF',
        }}>
          <span>4/4 steps</span>
          <span>2.3s</span>
          <span style={{ color: '#10B981' }}>$0.003</span>
        </div>
      )}
    </DemoPanel>
  )
}

// Step 4: Agent card carousel
function AgentDemo() {
  const agents = [
    { name: 'Classifier', color: '#3B82F6', desc: 'Classifies documents by type', icon: '\uD83D\uDD0D' },
    { name: 'Extractor', color: '#10B981', desc: 'Extracts entities from text', icon: '\uD83D\uDCC4' },
    { name: 'Critic', color: '#EF4444', desc: 'Evaluates output quality', icon: '\u2696\uFE0F' },
    { name: 'Repair', color: '#F59E0B', desc: 'Self-heals failed steps', icon: '\uD83D\uDD27' },
    { name: 'Planner', color: '#8B5CF6', desc: 'Decomposes complex tasks', icon: '\uD83D\uDDFA\uFE0F' },
  ]
  const [idx, setIdx] = useState(0)
  const [fade, setFade] = useState(true)
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    let cycle = 0
    const id = setInterval(() => {
      setFade(false)
      setTimeout(() => {
        cycle++
        if (cycle >= agents.length) { clearInterval(id); setPlaying(false); return }
        setIdx(cycle % agents.length)
        setFade(true)
      }, 200)
    }, 1500)
    setFade(true)
    return () => clearInterval(id)
  }, [])

  const a = agents[idx]
  return (
    <DemoPanel playing={playing}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14,
        opacity: fade ? 1 : 0,
        transform: fade ? 'translateX(0)' : 'translateX(-10px)',
        transition: 'all 0.25s ease',
        padding: '6px 0',
      }}>
        <div style={{
          width: 44, height: 44, borderRadius: 10,
          background: `${a.color}22`,
          border: `1px solid ${a.color}55`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20, flexShrink: 0,
        }}>
          {a.icon}
        </div>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: a.color }}>{a.name}</div>
          <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 2 }}>{a.desc}</div>
        </div>
      </div>
      {/* Dots */}
      <div style={{ display: 'flex', gap: 5, justifyContent: 'center', marginTop: 10 }}>
        {agents.map((_, i) => (
          <div key={i} style={{
            width: 6, height: 6, borderRadius: 3,
            background: i === idx ? a.color : 'rgba(255,255,255,0.1)',
            transition: 'background 0.3s',
          }} />
        ))}
      </div>
    </DemoPanel>
  )
}

// Step 5: Debate topology animation
function SwarmDemo({ lang }) {
  const [phase, setPhase] = useState(0)
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 600),   // Analyzer produces
      setTimeout(() => setPhase(2), 1400),  // Critic scores low
      setTimeout(() => setPhase(3), 2200),  // Feedback loops back
      setTimeout(() => setPhase(4), 3000),  // Analyzer produces again
      setTimeout(() => setPhase(5), 3600),  // Critic scores high
      setTimeout(() => setPlaying(false), 4000),
    ]
    return () => timers.forEach(clearTimeout)
  }, [])

  const boxStyle = (active) => ({
    padding: '8px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600,
    textAlign: 'center', minWidth: 80,
    background: active ? 'rgba(99,102,241,0.12)' : 'rgba(255,255,255,0.03)',
    border: active ? '1px solid rgba(99,102,241,0.5)' : '1px solid #374151',
    color: active ? '#C7D2FE' : '#6B7280',
    transition: 'all 0.3s',
  })

  return (
    <DemoPanel playing={playing}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'center' }}>
        {/* Row: Analyzer -> Critic */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={boxStyle(phase >= 1 && phase !== 3)}>Analyzer</div>
          <svg width="40" height="20" viewBox="0 0 40 20">
            <line x1="0" y1="10" x2="32" y2="10" stroke="#6366F1"
              strokeWidth={2} strokeDasharray="32"
              strokeDashoffset={phase >= 1 ? 0 : 32}
              style={{ transition: 'stroke-dashoffset 0.5s ease' }} />
            <polygon points="30,5 38,10 30,15" fill="#6366F1"
              opacity={phase >= 1 ? 1 : 0} style={{ transition: 'opacity 0.3s' }} />
          </svg>
          <div style={boxStyle(phase === 2 || phase === 5)}>Critic</div>
        </div>

        {/* Score display */}
        {phase >= 2 && (
          <div style={{
            fontSize: 12, fontWeight: 700, textAlign: 'center',
            color: phase >= 5 ? '#10B981' : phase >= 2 ? '#EF4444' : '#6B7280',
            transition: 'color 0.3s',
            padding: '4px 12px', borderRadius: 6,
            background: phase >= 5 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
          }}>
            {phase >= 5 ? 'Score: 82/100 \u2713' : 'Score: 45/100'}
          </div>
        )}

        {/* Feedback arrow (loops back) */}
        {phase >= 3 && phase < 5 && (
          <div style={{
            fontSize: 11, color: '#F59E0B', fontStyle: 'italic',
            display: 'flex', alignItems: 'center', gap: 6,
            opacity: phase === 3 ? 1 : 0.5,
            transition: 'opacity 0.3s',
          }}>
            <span>\u21A9</span>
            <span>{lang === 'es' ? 'Feedback: mejorar analisis' : 'Feedback: improve analysis'}</span>
          </div>
        )}

        {/* Final message */}
        {phase >= 5 && (
          <div style={{ fontSize: 11, color: '#10B981', fontWeight: 600, marginTop: 2 }}>
            {lang === 'es' ? 'Calidad mejorada por iteracion!' : 'Quality improved through iteration!'}
          </div>
        )}
      </div>
    </DemoPanel>
  )
}

// Step 6: RAG pipeline animation
function DocumentDemo({ lang }) {
  const [phase, setPhase] = useState(0)
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 400),
      setTimeout(() => setPhase(2), 900),
      setTimeout(() => setPhase(3), 1400),
      setTimeout(() => setPhase(4), 2000),
      setTimeout(() => setPhase(5), 2500),
      setTimeout(() => { setPhase(6); setPlaying(false) }, 3000),
    ]
    return () => timers.forEach(clearTimeout)
  }, [])

  const pipeBox = (label, active) => (
    <div style={{
      padding: '5px 10px', borderRadius: 6, fontSize: 10, fontWeight: 600,
      background: active ? 'rgba(99,102,241,0.12)' : 'rgba(255,255,255,0.03)',
      border: active ? '1px solid rgba(99,102,241,0.4)' : '1px solid #374151',
      color: active ? '#C7D2FE' : '#6B7280',
      transition: 'all 0.3s', whiteSpace: 'nowrap',
    }}>
      {label}
    </div>
  )

  const arrow = (active) => (
    <span style={{
      color: active ? '#6366F1' : '#374151',
      fontSize: 12, transition: 'color 0.3s',
    }}>{'\u2192'}</span>
  )

  return (
    <DemoPanel playing={playing}>
      {/* Indexing pipeline */}
      <div style={{ fontSize: 9, color: '#6B7280', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        {lang === 'es' ? 'Indexacion' : 'Indexing'}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
        {pipeBox('Document', phase >= 0)}
        {arrow(phase >= 1)}
        {pipeBox('Chunk (500c)', phase >= 1)}
        {arrow(phase >= 2)}
        {pipeBox('Embed (512d)', phase >= 2)}
        {arrow(phase >= 3)}
        {pipeBox('pgvector', phase >= 3)}
      </div>

      {/* Search pipeline */}
      {phase >= 4 && (
        <>
          <div style={{ fontSize: 9, color: '#6B7280', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            {lang === 'es' ? 'Busqueda' : 'Search'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
            {pipeBox('"financial risk"', phase >= 4)}
            {arrow(phase >= 5)}
            {pipeBox('Cosine', phase >= 5)}
            {arrow(phase >= 6)}
            {pipeBox('Top 3', phase >= 6)}
          </div>
        </>
      )}

      {/* Results */}
      {phase >= 6 && (
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 4 }}>
          {[94, 87, 72].map((pct, i) => (
            <span key={i} style={{
              fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 4,
              background: `rgba(16,185,129,${pct / 200})`,
              color: '#10B981',
            }}>
              {pct}%
            </span>
          ))}
        </div>
      )}
    </DemoPanel>
  )
}

// Step 7: Chat simulation
function ChatDemo({ lang }) {
  const [phase, setPhase] = useState(0)
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 500),   // User message
      setTimeout(() => setPhase(2), 1200),  // Typing dots
      setTimeout(() => { setPhase(3); setPlaying(false) }, 2500),  // Assistant response
    ]
    return () => timers.forEach(clearTimeout)
  }, [])

  const userQ = lang === 'es'
    ? 'Que agentes procesan datos?'
    : 'What agents handle data processing?'
  const botA = lang === 'es'
    ? '4 agentes: Classifier, Extractor, Normalizer, Validator. El Classifier identifica el tipo de documento...'
    : '4 agents: Classifier, Extractor, Normalizer, Validator. The Classifier identifies document type...'

  return (
    <DemoPanel playing={playing}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* User message */}
        {phase >= 1 && (
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <div style={{
              padding: '8px 12px', borderRadius: '10px 10px 2px 10px',
              background: 'rgba(99,102,241,0.2)', border: '1px solid rgba(99,102,241,0.3)',
              fontSize: 12, color: '#C7D2FE', maxWidth: '80%',
            }}>
              {userQ}
            </div>
          </div>
        )}
        {/* Typing indicator */}
        {phase === 2 && (
          <div style={{ display: 'flex', gap: 4, padding: '8px 12px' }}>
            {[0, 1, 2].map(i => (
              <div key={i} style={{
                width: 6, height: 6, borderRadius: 3, background: '#6366F1',
                animation: `nxfDemoPulse 0.8s infinite ${i * 0.2}s`,
              }} />
            ))}
          </div>
        )}
        {/* Bot response */}
        {phase >= 3 && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              padding: '8px 12px', borderRadius: '10px 10px 10px 2px',
              background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
              fontSize: 12, color: '#D1D5DB', maxWidth: '90%', lineHeight: 1.5,
            }}>
              {botA}
            </div>
          </div>
        )}
      </div>
    </DemoPanel>
  )
}

// ─── Tour Step Definitions ──────────────────────────────────────────────────

const TOUR_STEPS = [
  {
    page: 'dashboard',
    titleKey: 'dashboard',
    descKey: 'tourDemo1',
    DemoComponent: DashboardDemo,
  },
  {
    page: 'workflows',
    titleKey: 'workflows',
    descKey: 'tourDemo2',
    DemoComponent: WorkflowDemo,
  },
  {
    page: 'executions',
    titleKey: 'executions',
    descKey: 'tourDemo3',
    DemoComponent: ExecutionDemo,
  },
  {
    page: 'agents',
    titleKey: 'agents',
    descKey: 'tourDemo4',
    DemoComponent: AgentDemo,
  },
  {
    page: 'swarms',
    titleKey: 'swarms',
    descKey: 'tourDemo5',
    DemoComponent: SwarmDemo,
  },
  {
    page: 'documents',
    titleKey: 'documents',
    descKey: 'tourDemo6',
    DemoComponent: DocumentDemo,
  },
  {
    page: null,
    titleKey: 'chat',
    descKey: 'tourDemo7',
    DemoComponent: ChatDemo,
  },
]

// ─── Main Component ─────────────────────────────────────────────────────────

export default function OnboardingTour({ lang, onSetLang, onNavigate, onComplete }) {
  const [step, setStep] = useState(-1) // -1 = welcome, TOUR_STEPS.length = final
  const [fadeIn, setFadeIn] = useState(true)
  const [demoKey, setDemoKey] = useState(0) // force re-mount demos on step change

  // Fade transition on step change
  useEffect(() => {
    setFadeIn(false)
    const t1 = setTimeout(() => setFadeIn(true), 80)
    return () => clearTimeout(t1)
  }, [step])

  // Navigate to the correct page when step changes
  useEffect(() => {
    if (step >= 0 && step < TOUR_STEPS.length) {
      const s = TOUR_STEPS[step]
      if (s.page) onNavigate(s.page)
      setDemoKey(prev => prev + 1)
    }
  }, [step, onNavigate])

  const handleNext = () => {
    if (step < TOUR_STEPS.length - 1) {
      setStep(step + 1)
    } else if (step === TOUR_STEPS.length - 1) {
      setStep(TOUR_STEPS.length) // go to final screen
    } else {
      handleFinish()
    }
  }

  const handlePrev = () => {
    if (step === TOUR_STEPS.length) {
      setStep(TOUR_STEPS.length - 1)
    } else if (step > 0) {
      setStep(step - 1)
    }
  }

  const handleFinish = () => {
    try { localStorage.setItem('nxf-tour-done', 'true') } catch { /* */ }
    onComplete()
  }

  const totalSteps = TOUR_STEPS.length
  const isWelcome = step === -1
  const isFinal = step === TOUR_STEPS.length
  const progress = isWelcome ? 0 : isFinal ? 100 : ((step + 1) / totalSteps) * 100

  // ── Welcome Screen ──
  if (isWelcome) {
    return (
      <>
        <style>{tourKeyframes}</style>
        <div
          style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(4px)',
          }}
          role="dialog" aria-modal="true" aria-label="Onboarding tour"
        >
          <div
            style={{
              background: '#161E2E', borderRadius: 16,
              border: '1px solid rgba(99, 102, 241, 0.3)',
              padding: '48px 40px', maxWidth: 520, width: '90%', textAlign: 'center',
              opacity: fadeIn ? 1 : 0,
              transform: fadeIn ? 'translateY(0) scale(1)' : 'translateY(12px) scale(0.98)',
              transition: 'opacity 0.3s ease, transform 0.3s ease',
              boxShadow: '0 25px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(99, 102, 241, 0.1)',
            }}
          >
            <div style={{
              width: 64, height: 64, borderRadius: 16,
              background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 24px', fontSize: 24, fontWeight: 700, color: '#fff',
            }}>NF</div>
            <h1 style={{ fontSize: 26, fontWeight: 700, color: '#E5E7EB', marginBottom: 12 }}>
              {t('welcome', lang)}
            </h1>
            <p style={{ fontSize: 15, color: '#9CA3AF', lineHeight: 1.6, marginBottom: 24 }}>
              {t('welcomeDesc', lang)}
            </p>
            {/* Language selector */}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 28 }}>
              {['es', 'en'].map(l => (
                <button key={l}
                  onClick={() => onSetLang && onSetLang(l)}
                  aria-label={l === 'es' ? 'Espanol' : 'English'}
                  style={{
                    padding: '8px 20px', borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: 'pointer',
                    background: lang === l ? '#6366F1' : 'transparent',
                    color: lang === l ? '#fff' : '#9CA3AF',
                    border: lang === l ? '1px solid #6366F1' : '1px solid rgba(255,255,255,0.15)',
                    transition: 'all 0.2s ease',
                  }}
                >
                  {l === 'es' ? 'ES Espanol' : 'EN English'}
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button
                onClick={handleFinish}
                style={{
                  padding: '12px 24px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)',
                  background: 'transparent', color: '#9CA3AF', fontSize: 14,
                  fontWeight: 500, cursor: 'pointer', transition: 'all 0.2s',
                }}
              >
                {t('skip', lang)}
              </button>
              <button
                onClick={() => setStep(0)}
                style={{
                  padding: '12px 32px', borderRadius: 10, border: 'none',
                  background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
                  color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
                  transition: 'all 0.2s', boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)',
                }}
              >
                {t('next', lang)}
              </button>
            </div>
          </div>
        </div>
      </>
    )
  }

  // ── Final Screen ──
  if (isFinal) {
    return (
      <>
        <style>{tourKeyframes}</style>
        <div
          style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(4px)',
          }}
          role="dialog" aria-modal="true"
        >
          <div style={{
            background: '#161E2E', borderRadius: 16,
            border: '1px solid rgba(99,102,241,0.3)',
            padding: '48px 40px', maxWidth: 560, width: '90%', textAlign: 'center',
            opacity: fadeIn ? 1 : 0,
            transform: fadeIn ? 'translateY(0) scale(1)' : 'translateY(12px) scale(0.98)',
            transition: 'opacity 0.3s ease, transform 0.3s ease',
            boxShadow: '0 25px 60px rgba(0,0,0,0.5), 0 0 40px rgba(99,102,241,0.1)',
          }}>
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: 'linear-gradient(135deg, #10B981, #059669)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 24px', fontSize: 28, color: '#fff',
            }}>{'\u2713'}</div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 8 }}>
              {t('tourReady', lang)}
            </h1>
            <p style={{ fontSize: 14, color: '#9CA3AF', lineHeight: 1.6, marginBottom: 24 }}>
              {t('tourFinal', lang)}
            </p>
            {/* Stats grid */}
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10,
              marginBottom: 24,
            }}>
              {[
                { label: lang === 'es' ? '22 Agentes IA' : '22 AI Agents', color: '#6366F1' },
                { label: lang === 'es' ? '6 Topologias' : '6 Topologies', color: '#8B5CF6' },
                { label: lang === 'es' ? 'Memoria 3 Niveles' : '3-Tier Memory', color: '#10B981' },
                { label: 'Self-Healing', color: '#F59E0B' },
              ].map((s, i) => (
                <div key={i} style={{
                  padding: '10px 12px', borderRadius: 8,
                  background: `${s.color}10`, border: `1px solid ${s.color}33`,
                  fontSize: 12, fontWeight: 600, color: s.color,
                }}>
                  {s.label}
                </div>
              ))}
            </div>
            <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 20, lineHeight: 1.6 }}>
              Python FastAPI + React + PostgreSQL + Redis<br />
              {t('tourStats', lang)}
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button
                onClick={handlePrev}
                style={{
                  padding: '10px 20px', borderRadius: 10,
                  border: '1px solid rgba(99,102,241,0.2)',
                  background: 'transparent', color: '#818CF8', fontSize: 13,
                  fontWeight: 500, cursor: 'pointer',
                }}
              >
                {t('back', lang)}
              </button>
              <button
                onClick={handleFinish}
                style={{
                  padding: '14px 40px', borderRadius: 10, border: 'none',
                  background: 'linear-gradient(135deg, #10B981, #059669)',
                  color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer',
                  boxShadow: '0 4px 20px rgba(16,185,129,0.3)',
                  transition: 'all 0.2s',
                }}
              >
                {t('finish', lang)}
              </button>
            </div>
          </div>
        </div>
      </>
    )
  }

  // ── Tour Step with Demo ──
  const currentStep = TOUR_STEPS[step]
  const DemoComp = currentStep.DemoComponent
  const isChatStep = step === 6

  return (
    <>
      <style>{tourKeyframes}</style>

      {/* Full-screen overlay */}
      <div
        style={{
          position: 'fixed', inset: 0, zIndex: 9998,
          background: 'rgba(0, 0, 0, 0.65)',
          backdropFilter: 'blur(2px)',
        }}
        onClick={(e) => e.stopPropagation()}
      />

      {/* Centered demo tooltip panel */}
      <div
        role="dialog"
        aria-modal="false"
        aria-label={t(currentStep.descKey, lang)}
        style={{
          position: 'fixed',
          top: '50%', left: '50%',
          transform: fadeIn
            ? 'translate(-50%, -50%) scale(1)'
            : 'translate(-50%, -50%) scale(0.96)',
          zIndex: 9999,
          background: '#161E2E',
          borderRadius: 14,
          border: '1px solid rgba(99,102,241,0.3)',
          padding: '22px 26px 20px',
          width: isChatStep ? 420 : 450,
          maxWidth: '94vw',
          maxHeight: '90vh',
          overflowY: 'auto',
          boxShadow: '0 20px 60px rgba(0,0,0,0.7), 0 0 30px rgba(99,102,241,0.1)',
          opacity: fadeIn ? 1 : 0,
          transition: 'opacity 0.3s ease, transform 0.3s ease',
        }}
      >
        {/* Step counter badge */}
        <div style={{
          fontSize: 11, fontWeight: 700, color: '#818CF8',
          letterSpacing: '0.08em', marginBottom: 10,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span style={{
            padding: '2px 8px', borderRadius: 4,
            background: 'rgba(99,102,241,0.15)',
          }}>
            {step + 1} / {totalSteps}
          </span>
          <span style={{ color: '#4B5563', fontSize: 10 }}>
            {currentStep.page ? currentStep.page.toUpperCase() : 'ASSISTANT'}
          </span>
        </div>

        {/* Step title */}
        <h3 style={{
          fontSize: 18, fontWeight: 700, color: '#E5E7EB', margin: '0 0 6px',
        }}>
          {t(currentStep.titleKey, lang)}
        </h3>

        {/* Step description */}
        <p style={{
          fontSize: 13, color: '#9CA3AF', lineHeight: 1.6, margin: '0 0 0',
        }}>
          {t(currentStep.descKey, lang)}
        </p>

        {/* Live demo */}
        <DemoComp key={demoKey} lang={lang} />

        {/* Progress dots */}
        <div style={{
          display: 'flex', gap: 4, marginTop: 16, marginBottom: 14, justifyContent: 'center',
        }}>
          {Array.from({ length: totalSteps }, (_, i) => (
            <div
              key={i}
              onClick={() => setStep(i)}
              style={{
                width: i === step ? 20 : 6, height: 6, borderRadius: 3, cursor: 'pointer',
                background: i === step
                  ? 'linear-gradient(90deg, #6366F1, #8B5CF6)'
                  : i < step ? '#6366F1' : 'rgba(255,255,255,0.1)',
                transition: 'all 0.3s ease',
              }}
            />
          ))}
        </div>

        {/* Controls */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <button
            onClick={handleFinish}
            style={{
              padding: '8px 14px', borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.08)',
              background: 'transparent', color: '#6B7280', fontSize: 12,
              fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s',
            }}
          >
            {t('skip', lang)}
          </button>

          <div style={{ display: 'flex', gap: 8 }}>
            {step > 0 && (
              <button
                onClick={handlePrev}
                style={{
                  padding: '8px 16px', borderRadius: 8,
                  border: '1px solid rgba(99,102,241,0.2)',
                  background: 'transparent', color: '#818CF8', fontSize: 13,
                  fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s',
                }}
              >
                {t('back', lang)}
              </button>
            )}
            <button
              onClick={handleNext}
              style={{
                padding: '8px 22px', borderRadius: 8, border: 'none',
                background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
                color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                transition: 'all 0.2s',
                boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)',
              }}
            >
              {step === totalSteps - 1 ? t('next', lang) : t('next', lang)}
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div style={{
          height: 3, borderRadius: 2, background: 'rgba(255,255,255,0.06)',
          overflow: 'hidden', marginTop: 12,
        }}>
          <div style={{
            height: '100%', borderRadius: 2, width: `${progress}%`,
            background: 'linear-gradient(90deg, #6366F1, #8B5CF6)',
            transition: 'width 0.4s ease',
          }} />
        </div>
      </div>
    </>
  )
}

// ── Shared Keyframes ────────────────────────────────────────────────────────

const tourKeyframes = `
  @keyframes nxfDemoPulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.8); }
  }
  @keyframes nxfTourFade {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }
`
