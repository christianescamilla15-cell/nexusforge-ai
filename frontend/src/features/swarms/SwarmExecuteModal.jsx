import { useState, useEffect, useRef } from 'react'

const ALL_AGENTS = [
  'DocClassifier', 'EntityExtractor', 'SummaryAgent', 'ContentGen', 'FlowRouter',
  'DataValidator', 'SentimentAnalyzer', 'TranslationAgent', 'CodeReviewer', 'TestGenerator',
  'APIMapper', 'SchemaValidator', 'DataTransformer', 'ReportBuilder', 'AlertMonitor',
  'ComplianceChecker', 'PriorityRanker', 'DuplicateDetector', 'ContextLinker', 'AnomalyDetector',
  'FeedbackCollector', 'QualityAssurer',
]

const AGENT_TYPES = {
  DocClassifier: { type: 'classifier', color: '#6366F1' },
  EntityExtractor: { type: 'extractor', color: '#10B981' },
  SummaryAgent: { type: 'summarizer', color: '#F59E0B' },
  ContentGen: { type: 'generator', color: '#EC4899' },
  FlowRouter: { type: 'router', color: '#60A5FA' },
  DataValidator: { type: 'validator', color: '#8B5CF6' },
  SentimentAnalyzer: { type: 'analyzer', color: '#F97316' },
  TranslationAgent: { type: 'translator', color: '#14B8A6' },
  CodeReviewer: { type: 'reviewer', color: '#EF4444' },
  TestGenerator: { type: 'generator', color: '#EC4899' },
  APIMapper: { type: 'mapper', color: '#6366F1' },
  SchemaValidator: { type: 'validator', color: '#8B5CF6' },
  DataTransformer: { type: 'transformer', color: '#10B981' },
  ReportBuilder: { type: 'builder', color: '#F59E0B' },
  AlertMonitor: { type: 'monitor', color: '#EF4444' },
  ComplianceChecker: { type: 'checker', color: '#60A5FA' },
  PriorityRanker: { type: 'ranker', color: '#F97316' },
  DuplicateDetector: { type: 'detector', color: '#14B8A6' },
  ContextLinker: { type: 'linker', color: '#8B5CF6' },
  AnomalyDetector: { type: 'detector', color: '#14B8A6' },
  FeedbackCollector: { type: 'collector', color: '#6366F1' },
  QualityAssurer: { type: 'assurer', color: '#10B981' },
}

const LABELS = {
  en: {
    executeSwarm: 'Execute Swarm',
    selectAgents: 'Select at least 2 agents',
    executing: 'Executing...',
    agents: 'Agents',
    selected: 'selected',
    inputData: 'Input Data (JSON)',
    close: 'Close modal',
    configExecution: 'Select agents and configure execution',
    processing: 'Processing...',
    completed: 'Completed',
    receiving: 'Receiving input from',
    output: 'Output',
    pipelineComplete: 'Sequential pipeline complete',
    stepsIn: 'steps in',
    allStarting: 'All agents starting simultaneously...',
    aggregating: 'Aggregating results from',
    agentsLabel: 'agents',
    parallelComplete: 'Parallel execution complete',
    avgPerAgent: 'avg per agent',
    decomposing: 'Decomposing task into subtasks...',
    subtask: 'Subtask',
    workersExecuting: 'Workers executing subtasks...',
    synthesizing: 'Synthesizing results...',
    hierarchicalComplete: 'Hierarchical execution',
    planner: 'planner',
    workers: 'workers',
    total: 'total',
    analyzing: 'Analyzing...',
    evaluating: 'Evaluating...',
    score: 'Score',
    feedback: 'Feedback',
    needsMoreDetail: 'needs more detail on financial risk factors',
    goodImprovement: 'good improvement, missing regulatory context',
    improving: 'Improving based on feedback...',
    reEvaluating: 'Re-evaluating...',
    finalRevision: 'Final revision...',
    debateConverged: 'Debate converged in',
    rounds: 'rounds',
    quality: 'Quality',
    vote: 'vote',
    category: 'Category',
    financial: 'Financial',
    legal: 'Legal',
    analyzingVotes: 'Analyzing votes...',
    consensus: 'Consensus',
    agreement: 'agreement',
    consensusReached: 'Consensus reached',
    among: 'among',
    analyzingComplexity: 'Analyzing input complexity...',
    recommended: 'Recommended',
    topology: 'topology',
    qualityCheck: 'Quality check',
    adaptiveSelected: 'Adaptive selected',
    select: 'Select',
    deselect: 'Deselect',
    agent: 'agent',
  },
  es: {
    executeSwarm: 'Ejecutar Swarm',
    selectAgents: 'Selecciona al menos 2 agentes',
    executing: 'Ejecutando...',
    agents: 'Agentes',
    selected: 'seleccionados',
    inputData: 'Datos de entrada (JSON)',
    close: 'Cerrar modal',
    configExecution: 'Selecciona agentes y configura la ejecucion',
    processing: 'Procesando...',
    completed: 'Completado',
    receiving: 'Recibiendo datos de',
    output: 'Salida',
    pipelineComplete: 'Pipeline secuencial completo',
    stepsIn: 'pasos en',
    allStarting: 'Todos los agentes iniciando simultaneamente...',
    aggregating: 'Agregando resultados de',
    agentsLabel: 'agentes',
    parallelComplete: 'Ejecucion paralela completa',
    avgPerAgent: 'promedio por agente',
    decomposing: 'Descomponiendo tarea en subtareas...',
    subtask: 'Subtarea',
    workersExecuting: 'Workers ejecutando subtareas...',
    synthesizing: 'Sintetizando resultados...',
    hierarchicalComplete: 'Ejecucion jerarquica',
    planner: 'planificador',
    workers: 'workers',
    total: 'total',
    analyzing: 'Analizando...',
    evaluating: 'Evaluando...',
    score: 'Puntuacion',
    feedback: 'Retroalimentacion',
    needsMoreDetail: 'necesita mas detalle sobre factores de riesgo financiero',
    goodImprovement: 'buena mejora, falta contexto regulatorio',
    improving: 'Mejorando basado en retroalimentacion...',
    reEvaluating: 'Re-evaluando...',
    finalRevision: 'Revision final...',
    debateConverged: 'Debate convergido en',
    rounds: 'rondas',
    quality: 'Calidad',
    vote: 'voto',
    category: 'Categoria',
    financial: 'Financiero',
    legal: 'Legal',
    analyzingVotes: 'Analizando votos...',
    consensus: 'Consenso',
    agreement: 'acuerdo',
    consensusReached: 'Consenso alcanzado',
    among: 'entre',
    analyzingComplexity: 'Analizando complejidad del input...',
    recommended: 'Recomendado',
    topology: 'topologia',
    qualityCheck: 'Control de calidad',
    adaptiveSelected: 'Adaptivo selecciono',
    select: 'Seleccionar',
    deselect: 'Deseleccionar',
    agent: 'agente',
  },
}

function getLabel(key, lang) {
  return (LABELS[lang] || LABELS.en)[key] || LABELS.en[key] || key
}

// --- Simulation Step Component ---
function SimStep({ agent, status, message, output, borderColor, delay, score }) {
  const agentInfo = AGENT_TYPES[agent] || { type: 'agent', color: '#6366F1' }
  const isRunning = status === 'running'
  const isComplete = status === 'completed'
  const isFailed = status === 'failed'

  const leftBorder = isFailed ? '#EF4444' : isComplete ? '#10B981' : isRunning ? '#3B82F6' : '#E5E7EB'

  return (
    <div
      style={{
        background: '#F3F4F6',
        borderRadius: 8,
        padding: '10px 14px',
        borderLeft: `3px solid ${borderColor || leftBorder}`,
        marginBottom: 8,
        transition: 'all 0.4s ease',
        opacity: status === 'pending' ? 0.3 : 1,
        animation: isRunning ? 'pulseBlue 1.5s ease-in-out infinite' : 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: message || output ? 6 : 0 }}>
        {agent && (
          <>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{agent}</span>
            <span style={{
              fontSize: 10, padding: '1px 6px', borderRadius: 4,
              background: `${agentInfo.color}22`, color: agentInfo.color, fontWeight: 500,
            }}>
              {agentInfo.type}
            </span>
          </>
        )}
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4 }}>
          {isRunning && <span style={{ fontSize: 12, color: '#3B82F6' }}>...</span>}
          {isComplete && <span style={{ fontSize: 14, color: '#10B981' }}>&#10003;</span>}
          {isFailed && <span style={{ fontSize: 14, color: '#EF4444' }}>&#10007;</span>}
        </span>
        {score !== undefined && <ScoreBadge score={score} />}
      </div>
      {message && (
        <div style={{ fontSize: 12, color: '#9CA3AF', marginBottom: output ? 4 : 0 }}>{message}</div>
      )}
      {output && (
        <div style={{ fontSize: 12, color: '#374151', fontStyle: 'italic' }}>{output}</div>
      )}
    </div>
  )
}

function ScoreBadge({ score }) {
  const color = score >= 80 ? '#10B981' : score >= 60 ? '#F59E0B' : '#EF4444'
  const bg = score >= 80 ? 'rgba(16,185,129,0.15)' : score >= 60 ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)'
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 6,
      background: bg, color, border: `1px solid ${color}44`,
    }}>
      {score}/100
    </span>
  )
}

function FinalSummary({ text, duration }) {
  return (
    <div style={{
      background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.25)',
      borderRadius: 8, padding: '10px 14px', marginTop: 8,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981', flexShrink: 0 }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: '#10B981', flex: 1 }}>{text}</span>
        {duration && <span style={{ fontSize: 12, color: '#9CA3AF' }}>{duration}</span>}
      </div>
    </div>
  )
}

function ConnectorArrow() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '2px 0' }}>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M8 2 L8 12 M4 9 L8 13 L12 9" stroke="#4B5563" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  )
}

// --- Simulation Generators ---

function buildSequentialPhases(agents, lang) {
  const l = (k) => getLabel(k, lang)
  const phases = []
  const outputs = [
    'Classified: financial_report', 'Extracted: 12 entities', 'Summary: Q4 growth 15%',
    'Generated: executive brief', 'Routed: compliance_path', 'Validated: schema OK',
    'Sentiment: positive (0.82)', 'Translated: EN->ES complete', 'Review: 3 issues found',
  ]

  agents.forEach((agent, i) => {
    const steps = []
    if (i > 0) {
      steps.push({
        agent, status: 'running',
        message: `${l('receiving')} ${agents[i - 1]}...`,
        delay: 500,
      })
    }
    steps.push({
      agent, status: 'running',
      message: l('processing'),
      delay: 1000,
    })
    steps.push({
      agent, status: 'completed',
      message: l('completed'),
      output: `${l('output')}: ${outputs[i % outputs.length]}`,
      delay: 0,
    })
    phases.push(steps)
  })

  const totalTime = (agents.length * 1.5).toFixed(1)
  phases.push([{
    agent: null, status: 'final',
    message: `${l('pipelineComplete')}: ${agents.length} ${l('stepsIn')} ${totalTime}s`,
    delay: 0,
  }])

  return phases
}

function buildParallelPhases(agents, lang) {
  const l = (k) => getLabel(k, lang)
  const phases = []
  const outputs = [
    'Result: classification complete', 'Result: extraction done', 'Result: summary ready',
    'Result: content generated', 'Result: routing done', 'Result: validation passed',
  ]

  // Phase 1: all start
  phases.push([{
    agent: null, status: 'running',
    message: l('allStarting'),
    delay: 800,
    allAgents: agents.map(a => ({ agent: a, status: 'running', message: l('processing') })),
  }])

  // Phase 2: agents complete staggered
  agents.forEach((agent, i) => {
    phases.push([{
      agent, status: 'completed',
      output: outputs[i % outputs.length],
      delay: 400,
      completedIndex: i,
    }])
  })

  // Phase 3: aggregation
  phases.push([{
    agent: null, status: 'running',
    message: `${l('aggregating')} ${agents.length} ${l('agentsLabel')}...`,
    delay: 1000,
  }])

  const totalTime = (1.0 + agents.length * 0.4 + 1.0).toFixed(1)
  const avgMs = Math.round((parseFloat(totalTime) * 1000) / agents.length)
  phases.push([{
    agent: null, status: 'final',
    message: `${l('parallelComplete')}: ${agents.length} ${l('agentsLabel')} in ${totalTime}s (${avgMs}ms ${l('avgPerAgent')})`,
    delay: 0,
  }])

  return phases
}

function buildHierarchicalPhases(agents, lang) {
  const l = (k) => getLabel(k, lang)
  const phases = []
  const planner = agents[0]
  const workerAgents = agents.slice(1)
  const subtasks = [`${l('subtask')} 1: Data validation`, `${l('subtask')} 2: Entity extraction`, `${l('subtask')} 3: Report generation`]

  // Phase 1: planner decomposes
  phases.push([{
    agent: planner, status: 'running',
    message: l('decomposing'),
    delay: 1200,
  }])
  phases.push([{
    agent: planner, status: 'completed',
    output: subtasks.join(' | '),
    delay: 0,
    subtasks,
  }])

  // Phase 2: workers in parallel
  phases.push([{
    agent: null, status: 'running',
    message: l('workersExecuting'),
    delay: 500,
    allAgents: workerAgents.map((a, i) => ({
      agent: a, status: 'running',
      message: `${subtasks[i % subtasks.length]}`,
    })),
  }])

  workerAgents.forEach((agent, i) => {
    phases.push([{
      agent, status: 'completed',
      output: `${subtasks[i % subtasks.length]} - done`,
      delay: 600,
      completedIndex: i,
    }])
  })

  // Phase 3: planner synthesizes
  phases.push([{
    agent: planner, status: 'running',
    message: l('synthesizing'),
    delay: 1000,
  }])
  phases.push([{
    agent: planner, status: 'completed',
    output: `${l('completed')} - all subtasks merged`,
    delay: 0,
  }])

  const totalTime = (1.2 + workerAgents.length * 0.6 + 1.0).toFixed(1)
  phases.push([{
    agent: null, status: 'final',
    message: `${l('hierarchicalComplete')}: 1 ${l('planner')} + ${workerAgents.length} ${l('workers')}, ${totalTime}s ${l('total')}`,
    delay: 0,
  }])

  return phases
}

function buildDebatePhases(agents, lang) {
  const l = (k) => getLabel(k, lang)
  const phases = []
  const debater = agents[0]
  const critic = agents.length > 1 ? agents[1] : agents[0]
  const scores = [45, 78, 91]
  const feedbacks = [l('needsMoreDetail'), l('goodImprovement')]

  // Round 1
  phases.push([{ agent: debater, status: 'running', message: `${l('analyzing')}`, delay: 1000 }])
  phases.push([{
    agent: debater, status: 'completed',
    output: `${l('output')}: Initial analysis of Q4 financial data`,
    delay: 0,
  }])
  phases.push([{ agent: critic, status: 'running', message: `${l('evaluating')}`, delay: 600 }])
  phases.push([{
    agent: critic, status: 'failed',
    message: `${l('score')}: ${scores[0]}/100`,
    output: `${l('feedback')}: ${feedbacks[0]}`,
    delay: 0,
    score: scores[0],
    round: 1,
  }])

  // Round 2
  phases.push([{ agent: debater, status: 'running', message: `${l('improving')}`, delay: 1000 }])
  phases.push([{
    agent: debater, status: 'completed',
    output: `${l('output')}: Revised analysis with risk factor assessment`,
    delay: 0,
  }])
  phases.push([{ agent: critic, status: 'running', message: `${l('reEvaluating')}`, delay: 600 }])
  phases.push([{
    agent: critic, status: 'failed',
    message: `${l('score')}: ${scores[1]}/100`,
    output: `${l('feedback')}: ${feedbacks[1]}`,
    delay: 0,
    score: scores[1],
    round: 2,
  }])

  // Round 3
  phases.push([{ agent: debater, status: 'running', message: `${l('finalRevision')}`, delay: 1000 }])
  phases.push([{
    agent: debater, status: 'completed',
    output: `${l('output')}: Complete analysis with regulatory framework`,
    delay: 0,
  }])
  phases.push([{ agent: critic, status: 'running', message: `${l('evaluating')}`, delay: 500 }])
  phases.push([{
    agent: critic, status: 'completed',
    message: `${l('score')}: ${scores[2]}/100`,
    delay: 0,
    score: scores[2],
    round: 3,
  }])

  phases.push([{
    agent: null, status: 'final',
    message: `${l('debateConverged')} 3 ${l('rounds')}. ${l('quality')}: ${scores.join(' -> ')}`,
    delay: 0,
  }])

  return phases
}

function buildConsensusPhases(agents, lang) {
  const l = (k) => getLabel(k, lang)
  const phases = []
  const categories = [l('financial'), l('financial'), l('legal'), l('financial'), l('legal')]
  const judge = agents[agents.length - 1]
  const voters = agents.slice(0, -1).length >= 2 ? agents.slice(0, -1) : agents

  // Phase 1: votes
  voters.forEach((agent, i) => {
    phases.push([{
      agent, status: 'running',
      message: `${l('analyzing')}`,
      delay: 800,
    }])
    phases.push([{
      agent, status: 'completed',
      output: `${l('vote')}: ${l('category')}: ${categories[i % categories.length]}`,
      delay: 200,
    }])
  })

  // Count votes
  const financialCount = voters.filter((_, i) => categories[i % categories.length] === l('financial')).length
  const agreementPct = Math.round((financialCount / voters.length) * 100)

  // Phase 2: judge
  phases.push([{
    agent: judge, status: 'running',
    message: `${l('analyzingVotes')}`,
    delay: 1000,
  }])
  phases.push([{
    agent: judge, status: 'completed',
    output: `${l('consensus')}: ${l('financial')} (${financialCount}/${voters.length} ${l('agreement')})`,
    delay: 0,
  }])

  phases.push([{
    agent: null, status: 'final',
    message: `${l('consensusReached')}: ${agreementPct}% ${l('agreement')} ${l('among')} ${voters.length} ${l('agentsLabel')}`,
    delay: 0,
  }])

  return phases
}

function buildAdaptivePhases(agents, lang) {
  const l = (k) => getLabel(k, lang)
  const phases = []
  const router = agents[0]
  const chosenTopology = 'debate'

  // Phase 1: router analyzes
  phases.push([{
    agent: router, status: 'running',
    message: `${l('analyzingComplexity')}`,
    delay: 1200,
  }])
  phases.push([{
    agent: router, status: 'completed',
    output: `${l('recommended')}: ${chosenTopology.charAt(0).toUpperCase() + chosenTopology.slice(1)} ${l('topology')}`,
    delay: 0,
  }])

  // Phase 2: abbreviated debate
  const debater = agents.length > 1 ? agents[1] : agents[0]
  const critic = agents.length > 2 ? agents[2] : agents[0]

  phases.push([{ agent: debater, status: 'running', message: `${l('analyzing')}`, delay: 800 }])
  phases.push([{
    agent: debater, status: 'completed',
    output: `${l('output')}: Analysis complete`,
    delay: 0,
  }])
  phases.push([{ agent: critic, status: 'running', message: `${l('evaluating')}`, delay: 600 }])
  phases.push([{
    agent: critic, status: 'completed',
    message: `${l('score')}: 85/100`,
    delay: 0,
    score: 85,
  }])

  // Phase 3: quality check
  phases.push([{
    agent: router, status: 'running',
    message: `${l('qualityCheck')}...`,
    delay: 800,
  }])
  phases.push([{
    agent: router, status: 'completed',
    message: `${l('qualityCheck')}: 85/100`,
    delay: 0,
    score: 85,
  }])

  phases.push([{
    agent: null, status: 'final',
    message: `${l('adaptiveSelected')} '${chosenTopology}' ${l('topology')}. ${l('quality')}: 85/100`,
    delay: 0,
  }])

  return phases
}

// --- Simulation Runner ---

function useSimulation(topology, agents, lang, running) {
  const [steps, setSteps] = useState([])
  const [phaseIndex, setPhaseIndex] = useState(-1)
  const [done, setDone] = useState(false)
  const timeoutRef = useRef(null)
  const phasesRef = useRef([])

  useEffect(() => {
    if (!running || agents.length < 2) return

    setSteps([])
    setPhaseIndex(0)
    setDone(false)

    const builders = {
      sequential: buildSequentialPhases,
      parallel: buildParallelPhases,
      hierarchical: buildHierarchicalPhases,
      debate: buildDebatePhases,
      consensus: buildConsensusPhases,
      adaptive: buildAdaptivePhases,
    }

    const builder = builders[topology] || builders.sequential
    phasesRef.current = builder(agents, lang)
  }, [running, topology, agents.length])

  useEffect(() => {
    if (phaseIndex < 0 || phaseIndex >= phasesRef.current.length) return

    const phase = phasesRef.current[phaseIndex]
    if (!phase || phase.length === 0) return

    const step = phase[0]
    const delay = step.delay || 0

    const advance = () => {
      setSteps(prev => [...prev, step])
      if (phaseIndex + 1 >= phasesRef.current.length) {
        setDone(true)
      } else {
        setPhaseIndex(phaseIndex + 1)
      }
    }

    if (delay > 0) {
      timeoutRef.current = setTimeout(advance, delay)
    } else {
      // Use a minimal timeout to allow React to render
      timeoutRef.current = setTimeout(advance, 80)
    }

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [phaseIndex])

  return { steps, done }
}

// --- Main Simulation Display ---

function SimulationDisplay({ steps, done, topology, lang }) {
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [steps.length])

  // For parallel topology, track completed agents separately
  const parallelAgentStates = {}
  if (topology === 'parallel') {
    steps.forEach(step => {
      if (step.allAgents) {
        step.allAgents.forEach(a => {
          parallelAgentStates[a.agent] = 'running'
        })
      }
      if (step.completedIndex !== undefined && step.agent) {
        parallelAgentStates[step.agent] = 'completed'
      }
    })
  }

  const renderDebateRoundLabel = (round) => {
    const l = (k) => getLabel(k, lang)
    return (
      <div style={{
        fontSize: 11, fontWeight: 600, color: '#6366F1', textTransform: 'uppercase',
        letterSpacing: '0.5px', padding: '4px 0', marginTop: 6,
      }}>
        Round {round}
      </div>
    )
  }

  let currentRound = 0

  return (
    <div
      ref={scrollRef}
      style={{
        maxHeight: 350, overflowY: 'auto', paddingRight: 4,
      }}
    >
      {steps.map((step, i) => {
        const elements = []

        // Debate round labels
        if (topology === 'debate' && step.round && step.round !== currentRound) {
          currentRound = step.round
        }

        if (step.status === 'final') {
          elements.push(<FinalSummary key={`final-${i}`} text={step.message} />)
        } else if (step.allAgents) {
          // Parallel: show all agents
          elements.push(
            <div key={`all-${i}`}>
              <div style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 6 }}>{step.message}</div>
              {step.allAgents.map((a, j) => {
                const finalStatus = parallelAgentStates[a.agent] || a.status
                return (
                  <SimStep
                    key={`${a.agent}-${j}`}
                    agent={a.agent}
                    status={finalStatus}
                    message={finalStatus === 'completed' ? null : a.message}
                    output={finalStatus === 'completed' ?
                      steps.find(s => s.agent === a.agent && s.status === 'completed')?.output : null}
                  />
                )
              })}
            </div>
          )
        } else if (step.completedIndex !== undefined && topology === 'parallel') {
          // Skip individual parallel completion steps (handled above)
          return null
        } else {
          if (i > 0 && steps[i - 1]?.status !== 'final' && !steps[i - 1]?.allAgents && step.agent) {
            elements.push(<ConnectorArrow key={`arrow-${i}`} />)
          }
          elements.push(
            <SimStep
              key={`step-${i}`}
              agent={step.agent}
              status={step.status}
              message={step.message}
              output={step.output}
              score={step.score}
            />
          )
        }

        return <div key={i}>{elements}</div>
      })}

      {!done && steps.length > 0 && (
        <div style={{ textAlign: 'center', padding: '8px 0' }}>
          <span style={{
            display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
            background: '#3B82F6', animation: 'pulseBlue 1s ease-in-out infinite',
          }} />
        </div>
      )}
    </div>
  )
}

// --- Pulse animation keyframes injector ---
function PulseStyle() {
  return (
    <style>{`
      @keyframes pulseBlue {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
      }
      @keyframes fadeInStep {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
      }
    `}</style>
  )
}

// --- Main Modal ---

export default function SwarmExecuteModal({ topology, onClose, lang = 'es' }) {
  const [selectedAgents, setSelectedAgents] = useState([])
  const [inputData, setInputData] = useState('{\n  "task": "Analizar documentos del Q4",\n  "documents": ["doc_1.pdf", "doc_2.pdf"]\n}')
  const [executing, setExecuting] = useState(false)
  const [simulationRunning, setSimulationRunning] = useState(false)

  const l = (k) => getLabel(k, lang)

  const toggleAgent = (name) => {
    setSelectedAgents((prev) =>
      prev.includes(name) ? prev.filter((a) => a !== name) : [...prev, name]
    )
  }

  const { steps, done } = useSimulation(topology, selectedAgents, lang, simulationRunning)

  useEffect(() => {
    if (done) {
      setExecuting(false)
    }
  }, [done])

  const handleExecute = () => {
    if (selectedAgents.length < 2) return
    setExecuting(true)
    setSimulationRunning(false)
    // Reset and start fresh
    setTimeout(() => setSimulationRunning(true), 50)
  }

  const topName = topology.charAt(0).toUpperCase() + topology.slice(1)

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 100, backdropFilter: 'blur(4px)',
      }}
    >
      <PulseStyle />
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#FFFFFF', borderRadius: 16, padding: 28,
          width: '90%', maxWidth: 660, maxHeight: '88vh', overflowY: 'auto',
          border: '1px solid #E5E7EB',
          boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#111827', margin: 0 }}>
              {l('executeSwarm')}: {topName}
            </h2>
            <p style={{ fontSize: 13, color: '#9CA3AF', margin: '4px 0 0' }}>
              {l('configExecution')}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label={l('close')}
            style={{
              background: '#F3F4F6', border: 'none', borderRadius: 8,
              width: 34, height: 34, display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#6B7280', cursor: 'pointer', fontSize: 18,
            }}
          >
            x
          </button>
        </div>

        {/* Agent selection */}
        <div style={{ marginBottom: 18 }}>
          <label style={{ fontSize: 13, fontWeight: 600, color: '#111827', display: 'block', marginBottom: 8 }}>
            {l('agents')} ({selectedAgents.length} {l('selected')})
          </label>
          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: 6,
            maxHeight: 140, overflowY: 'auto', padding: 10,
            background: '#F3F4F6', borderRadius: 8,
          }}>
            {ALL_AGENTS.map((name) => {
              const sel = selectedAgents.includes(name)
              return (
                <button
                  key={name}
                  onClick={() => toggleAgent(name)}
                  aria-label={`${sel ? l('deselect') : l('select')} ${l('agent')} ${name}`}
                  aria-pressed={sel}
                  style={{
                    padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                    border: sel ? '1px solid rgba(99,102,241,0.4)' : '1px solid #E5E7EB',
                    background: sel ? 'rgba(99,102,241,0.15)' : '#F3F4F6',
                    color: sel ? '#818CF8' : '#9CA3AF',
                    cursor: 'pointer', transition: 'all 0.15s',
                  }}
                >
                  {sel ? '\u2713 ' : ''}{name}
                </button>
              )
            })}
          </div>
        </div>

        {/* Input data */}
        <div style={{ marginBottom: 18 }}>
          <label style={{ fontSize: 13, fontWeight: 600, color: '#111827', display: 'block', marginBottom: 8 }}>
            {l('inputData')}
          </label>
          <textarea
            value={inputData}
            onChange={(e) => setInputData(e.target.value)}
            aria-label={l('inputData')}
            rows={5}
            style={{
              width: '100%', padding: 12, borderRadius: 8, border: '1px solid #E5E7EB',
              background: '#F3F4F6', color: '#111827', fontSize: 13,
              fontFamily: 'monospace', resize: 'vertical', outline: 'none',
              boxSizing: 'border-box',
            }}
            onFocus={(e) => { e.target.style.borderColor = 'rgba(99,102,241,0.4)' }}
            onBlur={(e) => { e.target.style.borderColor = '#E5E7EB' }}
          />
        </div>

        {/* Execute button */}
        <button
          onClick={handleExecute}
          disabled={executing || selectedAgents.length < 2}
          aria-label={l('executeSwarm')}
          style={{
            width: '100%', padding: '11px 0', borderRadius: 8, border: 'none',
            background: executing || selectedAgents.length < 2
              ? 'rgba(99,102,241,0.2)' : 'linear-gradient(135deg, #2563EB, #3B82F6)',
            color: executing || selectedAgents.length < 2 ? '#6366F1' : '#fff',
            fontSize: 14, fontWeight: 600, cursor: executing || selectedAgents.length < 2 ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s', marginBottom: 16,
          }}
        >
          {executing ? l('executing') : selectedAgents.length < 2 ? l('selectAgents') : l('executeSwarm')}
        </button>

        {/* Simulation Result */}
        {simulationRunning && steps.length > 0 && (
          <div style={{
            background: '#F3F4F6', border: '1px solid #E5E7EB',
            borderRadius: 10, padding: 16, animation: 'fadeInStep 0.3s ease-out',
          }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#9CA3AF', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              {topName} Simulation
            </div>
            <SimulationDisplay steps={steps} done={done} topology={topology} lang={lang} />
          </div>
        )}
      </div>
    </div>
  )
}
