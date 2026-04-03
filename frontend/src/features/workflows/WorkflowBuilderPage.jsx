import { useState, useEffect, useRef, useCallback } from 'react'
import { fetchAPI } from '../../services/api'

// ── Constants ────────────────────────────────────────────────────────────────

const NODE_W = 180
const NODE_H = 72
const AGENT_COLORS = {
  classifier: '#2563EB', extractor: '#059669', summarizer: '#7C3AED',
  analyzer: '#D97706', enricher: '#0891B2', validator: '#DC2626',
  reporter: '#DB2777', repair: '#6366F1', normalizer: '#0D9488',
  researcher: '#B45309', translator: '#4F46E5', compliance: '#BE185D',
  monitor: '#0369A1', router_agent: '#7C2D12', critic: '#15803D',
  planner: '#9333EA', knowledge: '#1D4ED8', scraper: '#B91C1C',
  ocr: '#0F766E', sentiment: '#C2410C', scheduler: '#6D28D9',
  webhook: '#374151', judge: '#1E40AF', router: '#065F46',
}

function agentColor(type) {
  return AGENT_COLORS[type] || '#6B7280'
}

// ── SVG edge between two nodes ───────────────────────────────────────────────

function Edge({ fromNode, toNode, onDelete }) {
  const x1 = fromNode.x + NODE_W
  const y1 = fromNode.y + NODE_H / 2
  const x2 = toNode.x
  const y2 = toNode.y + NODE_H / 2
  const cx1 = x1 + Math.max(60, (x2 - x1) * 0.5)
  const cx2 = x2 - Math.max(60, (x2 - x1) * 0.5)
  const mx = (x1 + x2) / 2
  const my = (y1 + y2) / 2

  return (
    <g>
      <path
        d={`M${x1},${y1} C${cx1},${y1} ${cx2},${y2} ${x2},${y2}`}
        fill="none" stroke="#6366F1" strokeWidth="2"
        markerEnd="url(#arrow)"
      />
      {/* invisible wider hit area */}
      <path
        d={`M${x1},${y1} C${cx1},${y1} ${cx2},${y2} ${x2},${y2}`}
        fill="none" stroke="transparent" strokeWidth="12"
        style={{ cursor: 'pointer' }}
        onClick={onDelete}
      />
      {/* delete dot */}
      <circle cx={mx} cy={my} r={8} fill="#EF4444" style={{ cursor: 'pointer' }} onClick={onDelete} />
      <text x={mx} y={my + 4} textAnchor="middle" fill="#fff" fontSize="11" style={{ pointerEvents: 'none' }}>×</text>
    </g>
  )
}

// ── Single agent node ────────────────────────────────────────────────────────

function AgentNode({ node, selected, connecting, onMouseDown, onDelete, onPortMouseDown, onPortMouseUp }) {
  const color = agentColor(node.agent_type)
  const border = selected ? '#6366F1' : connecting ? '#F59E0B' : '#E5E7EB'

  return (
    <g transform={`translate(${node.x},${node.y})`}>
      {/* shadow */}
      <rect x="2" y="4" width={NODE_W} height={NODE_H} rx="10" fill="rgba(0,0,0,0.08)" />
      {/* card */}
      <rect
        width={NODE_W} height={NODE_H} rx="10"
        fill="#fff" stroke={border} strokeWidth={selected ? 2 : 1}
        style={{ cursor: 'grab', filter: selected ? 'drop-shadow(0 0 6px rgba(99,102,241,0.4))' : 'none' }}
        onMouseDown={onMouseDown}
      />
      {/* color bar */}
      <rect width="6" height={NODE_H} rx="3" fill={color} />
      {/* agent type badge */}
      <rect x="14" y="10" width={NODE_W - 44} height="18" rx="4" fill={color + '18'} />
      <text x="20" y="23" fill={color} fontSize="10" fontWeight="700" fontFamily="monospace">
        {node.agent_type.toUpperCase()}
      </text>
      {/* name */}
      <text x="14" y="52" fill="#374151" fontSize="12" fontWeight="600">
        {node.name.length > 20 ? node.name.slice(0, 19) + '…' : node.name}
      </text>
      {/* delete button */}
      <g style={{ cursor: 'pointer' }} onClick={onDelete}>
        <rect x={NODE_W - 22} y="8" width="16" height="16" rx="4" fill="#FEE2E2" />
        <text x={NODE_W - 14} y="20" textAnchor="middle" fill="#EF4444" fontSize="12" fontWeight="700">×</text>
      </g>
      {/* output port (right) */}
      <circle
        cx={NODE_W} cy={NODE_H / 2} r={6}
        fill="#6366F1" stroke="#fff" strokeWidth="2"
        style={{ cursor: 'crosshair' }}
        onMouseDown={(e) => { e.stopPropagation(); onPortMouseDown(e, node.id, 'out') }}
      />
      {/* input port (left) */}
      <circle
        cx={0} cy={NODE_H / 2} r={6}
        fill="#10B981" stroke="#fff" strokeWidth="2"
        style={{ cursor: 'crosshair' }}
        onMouseUp={(e) => { e.stopPropagation(); onPortMouseUp(e, node.id) }}
      />
    </g>
  )
}

// ── Sidebar agent item ───────────────────────────────────────────────────────

const AGENT_DESCRIPTIONS = {
  classifier: { es: 'Clasifica documentos en categorías: legal, financiero, técnico, médico, general.', en: 'Classifies documents into categories: legal, financial, technical, medical, general.' },
  extractor: { es: 'Extrae datos estructurados (entidades, campos, tablas) de texto no estructurado.', en: 'Extracts structured data (entities, fields, tables) from unstructured text.' },
  summarizer: { es: 'Genera resúmenes concisos de documentos largos o resultados multi-paso.', en: 'Generates concise summaries of long documents or multi-step outputs.' },
  analyzer: { es: 'Análisis profundo: sentimiento, tendencias, anomalías, comparaciones.', en: 'Deep analysis: sentiment, trends, anomalies, comparisons.' },
  enricher: { es: 'Enriquece datos cruzando fuentes externas y base de conocimiento.', en: 'Enriches data by cross-referencing external sources and knowledge base.' },
  validator: { es: 'Valida completitud, consistencia y precisión de resultados.', en: 'Validates completeness, consistency, and accuracy of outputs.' },
  reporter: { es: 'Genera reportes formateados (Markdown, JSON) de resultados.', en: 'Generates formatted reports (Markdown, JSON) from results.' },
  repair: { es: 'Diagnostica fallos y sugiere correcciones automáticas.', en: 'Diagnoses failures and suggests automatic fixes.' },
  normalizer: { es: 'Limpia y normaliza datos, elimina duplicados.', en: 'Cleans and normalizes data, removes duplicates.' },
  researcher: { es: 'Investigación de temas con citaciones y fuentes.', en: 'Topic research with citations and sources.' },
  translator: { es: 'Traducción multi-idioma con preservación de contexto.', en: 'Multi-language translation with context preservation.' },
  compliance: { es: 'Verificación de reglas regulatorias y cumplimiento.', en: 'Regulatory rule checking and compliance verification.' },
  monitor: { es: 'Monitoreo de métricas de salud del sistema.', en: 'System health metrics monitoring.' },
  router_agent: { es: 'Recomienda y enruta al agente correcto según la tarea.', en: 'Recommends and routes to the correct agent based on task.' },
  critic: { es: 'Evaluación de calidad y crítica constructiva de resultados.', en: 'Quality scoring and constructive critique of outputs.' },
  planner: { es: 'Descomposición de tareas y planificación de pasos.', en: 'Task decomposition and step planning.' },
  knowledge: { es: 'Respuestas con RAG — busca en base de conocimiento.', en: 'Q&A with RAG — searches knowledge base.' },
  scraper: { es: 'Web scraping con selectores configurables.', en: 'Web scraping with configurable selectors.' },
  ocr: { es: 'Extracción de texto de imágenes y documentos escaneados.', en: 'Text extraction from images and scanned documents.' },
  sentiment: { es: 'Análisis de emociones, tono y temas principales.', en: 'Emotion, tone, and topic analysis.' },
  scheduler: { es: 'Programación y ordenamiento de tareas.', en: 'Task scheduling and ordering.' },
  webhook: { es: 'Invocación de callbacks HTTP a URLs externas.', en: 'HTTP callback invocation to external URLs.' },
  judge: { es: 'Juez imparcial para debates y decisiones entre agentes.', en: 'Impartial judge for debates and decisions between agents.' },
  router: { es: 'Enrutador dinámico que selecciona agentes por input.', en: 'Dynamic router that selects agents based on input.' },
}

function SidebarAgent({ agent, onDragStart, lang = 'en' }) {
  const color = agentColor(agent.agent_type)
  const [tooltipPos, setTooltipPos] = useState(null)
  const desc = AGENT_DESCRIPTIONS[agent.agent_type]
  const tooltipText = desc ? (desc[lang] || desc.en) : (agent.description || agent.name)

  const handleMouseEnter = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    setTooltipPos({ top: rect.top, left: rect.right + 8 })
  }
  const handleMouseLeave = () => setTooltipPos(null)

  return (
    <div style={{ marginBottom: 4 }}>
      <div
        draggable
        onDragStart={(e) => onDragStart(e, agent)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '7px 10px', borderRadius: 8,
          border: '1px solid #E5E7EB', background: '#fff',
          cursor: 'grab', userSelect: 'none', transition: 'box-shadow 0.15s',
        }}
        onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)'}
        onMouseLeave={(e) => e.currentTarget.style.boxShadow = 'none'}
      >
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: '#374151', flex: 1 }}>
          {agent.agent_type}
        </span>
        <div
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          style={{
            width: 16, height: 16, borderRadius: '50%',
            background: '#F3F4F6', display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'help', flexShrink: 0,
          }}
        >
          <span style={{ fontSize: 10, fontWeight: 700, color: '#9CA3AF' }}>i</span>
        </div>
      </div>

      {tooltipPos && (
        <div style={{
          position: 'fixed', left: tooltipPos.left, top: tooltipPos.top,
          width: 220, zIndex: 9999,
          background: '#1F2937', color: '#F9FAFB', padding: '10px 12px',
          borderRadius: 10, fontSize: 11, lineHeight: 1.5,
          boxShadow: '0 8px 24px rgba(0,0,0,0.25)',
          pointerEvents: 'none',
        }}>
          <div style={{ fontWeight: 700, marginBottom: 4, color }}>
            {agent.agent_type}
          </div>
          {tooltipText}
        </div>
      )}
    </div>
  )
}

// ── Demo workflows for edit fallback ─────────────────────────────────────────

const DEMO_WORKFLOW_STEPS = {
  'wf-1': { name: 'Análisis de Documentos', steps: [
    { name: 'ingest', type: 'extractor', depends_on: [] },
    { name: 'classify', type: 'classifier', depends_on: ['ingest'] },
    { name: 'summarize', type: 'summarizer', depends_on: ['classify'] },
    { name: 'validate', type: 'validator', depends_on: ['summarize'] },
  ]},
  'wf-2': { name: 'Clasificación de Datos', steps: [
    { name: 'load_data', type: 'extractor', depends_on: [] },
    { name: 'preprocess', type: 'normalizer', depends_on: ['load_data'] },
    { name: 'classify_a', type: 'classifier', depends_on: ['preprocess'] },
    { name: 'classify_b', type: 'classifier', depends_on: ['preprocess'] },
    { name: 'merge', type: 'enricher', depends_on: ['classify_a', 'classify_b'] },
    { name: 'export', type: 'validator', depends_on: ['merge'] },
  ]},
  'wf-3': { name: 'Resumen Ejecutivo', steps: [
    { name: 'extract', type: 'extractor', depends_on: [] },
    { name: 'summarize', type: 'summarizer', depends_on: ['extract'] },
  ]},
  'wf-4': { name: 'Extracción de Entidades', steps: [
    { name: 'ingest', type: 'extractor', depends_on: [] },
    { name: 'ner', type: 'extractor', depends_on: ['ingest'] },
    { name: 'validate', type: 'validator', depends_on: ['ner'] },
  ]},
  'wf-5': { name: 'Pipeline RAG', steps: [
    { name: 'upload', type: 'extractor', depends_on: [] },
    { name: 'chunk', type: 'normalizer', depends_on: ['upload'] },
    { name: 'embed', type: 'enricher', depends_on: ['chunk'] },
    { name: 'index', type: 'validator', depends_on: ['embed'] },
    { name: 'search', type: 'knowledge', depends_on: ['index'] },
  ]},
  'wf-6': { name: 'Traducción Masiva', steps: [
    { name: 'extract', type: 'extractor', depends_on: [] },
    { name: 'translate', type: 'translator', depends_on: ['extract'] },
    { name: 'review', type: 'critic', depends_on: ['translate'] },
  ]},
}

/** Convert a steps array into nodes + edges with consistent field names. */
function stepsToGraph(steps) {
  const newNodes = steps.map((step, i) => ({
    id: `node-${i}`,
    name: step.name,
    agent_type: step.type || step.agent_type || 'extractor',
    x: 80 + (i % 4) * 220,
    y: 80 + Math.floor(i / 4) * 140,
  }))
  const newEdges = []
  steps.forEach((step, i) => {
    (step.depends_on || []).forEach((dep) => {
      const fromIdx = steps.findIndex((s) => s.name === dep)
      if (fromIdx >= 0) newEdges.push({ from: `node-${fromIdx}`, to: `node-${i}` })
    })
  })
  return { nodes: newNodes, edges: newEdges }
}

export default function WorkflowBuilderPage({ lang = 'en', editWorkflowId = null, onNavigate }) {
  const [agents, setAgents] = useState([])
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([]) // [{from: nodeId, to: nodeId}]
  const [selected, setSelected] = useState(null)
  const [workflowName, setWorkflowName] = useState('My Workflow')
  const [saving, setSaving] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [toast, setToast] = useState(null)
  const [search, setSearch] = useState('')

  // Drag-node state
  const draggingNode = useRef(null)
  const dragOffset = useRef({ x: 0, y: 0 })

  // Edge-drawing state
  const connectingFrom = useRef(null) // nodeId
  const [pendingLine, setPendingLine] = useState(null) // {x1,y1,x2,y2}

  const canvasRef = useRef(null)
  const svgRef = useRef(null)
  const nodeCounter = useRef(0)

  // ── Load agents + existing workflow (if editing) ────────────────────────────

  useEffect(() => {
    fetchAPI('/agents').then((res) => {
      if (!res.error && res.data) {
        setAgents(Array.isArray(res.data) ? res.data : [])
      }
    })
  }, [])

  // Load workflow when editWorkflowId changes (prop-driven, works on re-mount too)
  useEffect(() => {
    if (!editWorkflowId) return

    // Demo workflow — load from local data immediately, no API call needed
    if (DEMO_WORKFLOW_STEPS[editWorkflowId]) {
      const demo = DEMO_WORKFLOW_STEPS[editWorkflowId]
      setWorkflowName(demo.name)
      const { nodes: n, edges: e } = stepsToGraph(demo.steps)
      nodeCounter.current = n.length
      setNodes(n)
      setEdges(e)
      return
    }

    // Real workflow — fetch from API
    fetchAPI(`/workflows/${editWorkflowId}`).then((res) => {
      if (!res.error && res.data) {
        const wf = res.data
        setWorkflowName(wf.name || 'Edited Workflow')
        const steps = wf.dag_definition?.steps || wf.dag?.steps || wf.steps || []
        if (steps.length > 0) {
          const { nodes: n, edges: e } = stepsToGraph(steps)
          nodeCounter.current = n.length
          setNodes(n)
          setEdges(e)
        }
      }
    })
  }, [editWorkflowId])

  const showToast = useCallback((msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }, [])

  // ── Drag from sidebar → drop on canvas ────────────────────────────────────

  const handleSidebarDragStart = (e, agent) => {
    e.dataTransfer.setData('agent_type', agent.agent_type)
    e.dataTransfer.setData('agent_name', agent.name || agent.agent_type)
  }

  const handleCanvasDrop = (e) => {
    e.preventDefault()
    const agent_type = e.dataTransfer.getData('agent_type')
    const agent_name = e.dataTransfer.getData('agent_name')
    if (!agent_type) return

    const rect = canvasRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left - NODE_W / 2
    const y = e.clientY - rect.top - NODE_H / 2

    nodeCounter.current += 1
    const id = `node_${nodeCounter.current}`
    setNodes((prev) => [...prev, {
      id,
      name: `${agent_type}_${nodeCounter.current}`,
      agent_type,
      x: Math.max(0, x),
      y: Math.max(0, y),
    }])
  }

  // ── Node drag (move on canvas) ─────────────────────────────────────────────

  const handleNodeMouseDown = (e, nodeId) => {
    e.stopPropagation()
    setSelected(nodeId)
    const node = nodes.find((n) => n.id === nodeId)
    draggingNode.current = nodeId
    dragOffset.current = { x: e.clientX - node.x, y: e.clientY - node.y }
  }

  const handleCanvasMouseMove = useCallback((e) => {
    if (draggingNode.current) {
      const x = e.clientX - dragOffset.current.x
      const y = e.clientY - dragOffset.current.y
      setNodes((prev) => prev.map((n) =>
        n.id === draggingNode.current ? { ...n, x: Math.max(0, x), y: Math.max(0, y) } : n
      ))
    }
    if (connectingFrom.current && svgRef.current) {
      const rect = svgRef.current.getBoundingClientRect()
      setPendingLine((prev) => prev ? { ...prev, x2: e.clientX - rect.left, y2: e.clientY - rect.top } : null)
    }
  }, [])

  const handleCanvasMouseUp = useCallback(() => {
    draggingNode.current = null
    connectingFrom.current = null
    setPendingLine(null)
  }, [])

  // ── Port interactions (draw edges) ─────────────────────────────────────────

  const handlePortMouseDown = (e, nodeId) => {
    e.preventDefault()
    connectingFrom.current = nodeId
    const node = nodes.find((n) => n.id === nodeId)
    const rect = svgRef.current.getBoundingClientRect()
    setPendingLine({
      x1: node.x + NODE_W,
      y1: node.y + NODE_H / 2,
      x2: e.clientX - rect.left,
      y2: e.clientY - rect.top,
    })
  }

  const handlePortMouseUp = (e, toNodeId) => {
    if (!connectingFrom.current || connectingFrom.current === toNodeId) return
    const from = connectingFrom.current
    // Prevent duplicate edges
    const exists = edges.some((ed) => ed.from === from && ed.to === toNodeId)
    if (!exists) {
      setEdges((prev) => [...prev, { from, to: toNodeId }])
    }
    connectingFrom.current = null
    setPendingLine(null)
  }

  const deleteEdge = (from, to) => {
    setEdges((prev) => prev.filter((e) => !(e.from === from && e.to === to)))
  }

  const deleteNode = (nodeId) => {
    setNodes((prev) => prev.filter((n) => n.id !== nodeId))
    setEdges((prev) => prev.filter((e) => e.from !== nodeId && e.to !== nodeId))
    if (selected === nodeId) setSelected(null)
  }

  // ── Build DAG definition ───────────────────────────────────────────────────

  const buildSteps = () => nodes.map((node) => ({
    name: node.name,
    type: node.agent_type,
    depends_on: edges.filter((e) => e.to === node.id).map((e) => {
      const fromNode = nodes.find((n) => n.id === e.from)
      return fromNode?.name || e.from
    }),
  }))

  // ── Save workflow ──────────────────────────────────────────────────────────

  const [currentSavedId, setCurrentSavedId] = useState(editWorkflowId || null)

  const handleSave = async () => {
    if (nodes.length === 0) { showToast(lang === 'es' ? 'Agrega al menos un nodo' : 'Add at least one agent node', 'error'); return }

    const body = {
      name: workflowName,
      description: lang === 'es' ? `Flujo de ${nodes.length} pasos` : `${nodes.length} steps workflow`,
      dag_definition: { steps: buildSteps() },
    }

    if (currentSavedId) {
      const overwrite = confirm(
        lang === 'es'
          ? '¿Sobreescribir el flujo existente?\n\nAceptar = Sobreescribir\nCancelar = Guardar como nuevo'
          : 'Overwrite existing workflow?\n\nOK = Overwrite\nCancel = Save as new'
      )
      if (overwrite) {
        setSaving(true)
        const res = await fetchAPI(`/workflows/${currentSavedId}`, { method: 'PUT', body: JSON.stringify(body) })
        setSaving(false)
        showToast(res.error
          ? `${lang === 'es' ? 'Error' : 'Failed'}: ${res.error}`
          : (lang === 'es' ? `"${workflowName}" actualizado` : `"${workflowName}" updated`),
          res.error ? 'error' : 'success')
        return
      }
    }

    setSaving(true)
    const res = await fetchAPI('/workflows', { method: 'POST', body: JSON.stringify(body) })
    setSaving(false)
    if (res.error) {
      showToast(`${lang === 'es' ? 'Error al guardar' : 'Save failed'}: ${res.error}`, 'error')
    } else {
      if (res.data?.id) setCurrentSavedId(res.data.id)
      showToast(lang === 'es' ? `"${workflowName}" guardado` : `"${workflowName}" saved`)
    }
  }

  // ── Execute workflow ───────────────────────────────────────────────────────

  const handleExecute = async () => {
    if (nodes.length === 0) { showToast(lang === 'es' ? 'Agrega al menos un nodo' : 'Add at least one agent node', 'error'); return }
    setExecuting(true)
    // Save first, then execute with workflow_id
    const saveRes = await fetchAPI('/workflows', {
      method: 'POST',
      body: JSON.stringify({
        name: workflowName,
        dag_definition: { steps: buildSteps() },
      }),
    })
    if (saveRes.error || !saveRes.data?.id) {
      showToast(`${lang === 'es' ? 'Error al guardar' : 'Save failed'}: ${saveRes.error || 'unknown'}`, 'error')
      setExecuting(false)
      return
    }
    const execRes = await fetchAPI('/executions', {
      method: 'POST',
      body: JSON.stringify({
        workflow_id: saveRes.data.id,
        trigger_type: 'manual',
        input_data: { source: 'builder' },
      }),
    })
    setExecuting(false)
    if (execRes.error) {
      showToast(`${lang === 'es' ? 'Error al ejecutar' : 'Execute failed'}: ${execRes.error}`, 'error')
    } else {
      showToast(lang === 'es' ? 'Ejecución iniciada' : 'Execution started')
    }
  }

  const clearCanvas = () => { setNodes([]); setEdges([]); setSelected(null) }

  const filteredAgents = agents.filter((a) =>
    a.agent_type.includes(search.toLowerCase()) || (a.name || '').toLowerCase().includes(search.toLowerCase())
  )

  // ── Builder Menu Actions ──────────────────────────────────────────────────

  const [showBuilderMenu, setShowBuilderMenu] = useState(false)
  const fileInputRef = useRef(null)

  const handleDuplicate = () => {
    setWorkflowName(workflowName + ' (Copy)')
    setCurrentSavedId(null) // force create new on next save
    showToast(lang === 'es' ? 'Flujo duplicado — guarda para crear copia' : 'Workflow duplicated — save to create copy')
    setShowBuilderMenu(false)
  }

  const handleExportJSON = () => {
    const data = {
      name: workflowName,
      dag_definition: { steps: buildSteps() },
      exported_at: new Date().toISOString(),
      nodes_layout: nodes.map(n => ({ id: n.id, x: n.x, y: n.y })),
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${workflowName.replace(/\s+/g, '_')}.json`
    a.click()
    URL.revokeObjectURL(url)
    showToast(lang === 'es' ? 'JSON exportado' : 'JSON exported')
    setShowBuilderMenu(false)
  }

  const handleImportJSON = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (evt) => {
      try {
        const data = JSON.parse(evt.target.result)
        if (data.name) setWorkflowName(data.name)
        const steps = data.dag_definition?.steps || data.steps || []
        if (steps.length > 0) {
          const { nodes: n, edges: ed } = stepsToGraph(steps)
          // Apply saved layout if available
          if (data.nodes_layout) {
            n.forEach(node => {
              const layout = data.nodes_layout.find(l => l.id === node.id)
              if (layout) { node.x = layout.x; node.y = layout.y }
            })
          }
          setNodes(n)
          setEdges(ed)
          nodeCounter.current = steps.length
          setCurrentSavedId(null)
          showToast(lang === 'es' ? `Importado: ${steps.length} pasos` : `Imported: ${steps.length} steps`)
        }
      } catch {
        showToast(lang === 'es' ? 'Error al leer JSON' : 'Failed to parse JSON', 'error')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
    setShowBuilderMenu(false)
  }

  const handleAutoConnect = () => {
    if (nodes.length < 2) return
    const newEdges = []
    for (let i = 0; i < nodes.length - 1; i++) {
      newEdges.push({ from: nodes[i].id, to: nodes[i + 1].id })
    }
    setEdges(newEdges)
    showToast(lang === 'es' ? `${newEdges.length} conexiones creadas` : `${newEdges.length} connections created`)
    setShowBuilderMenu(false)
  }

  const handleAutoLayout = () => {
    if (nodes.length === 0) return
    const cols = Math.ceil(Math.sqrt(nodes.length))
    const newNodes = nodes.map((n, i) => ({
      ...n,
      x: 60 + (i % cols) * 220,
      y: 60 + Math.floor(i / cols) * 120,
    }))
    setNodes(newNodes)
    showToast(lang === 'es' ? 'Nodos reorganizados' : 'Nodes reorganized')
    setShowBuilderMenu(false)
  }

  const handleRegenerate = () => {
    if (onNavigate) onNavigate('wizard')
    setShowBuilderMenu(false)
  }

  const handleViewHistory = async () => {
    if (!currentSavedId && !editWorkflowId) {
      showToast(lang === 'es' ? 'Guarda el flujo primero' : 'Save the workflow first', 'error')
      setShowBuilderMenu(false)
      return
    }
    const id = currentSavedId || editWorkflowId
    const res = await fetchAPI(`/runs`)
    if (!res.error && res.data?.runs) {
      const count = res.data.runs.length
      showToast(lang === 'es' ? `${count} ejecuciones en total` : `${count} total executions`)
    }
    setShowBuilderMenu(false)
  }

  const BUILDER_MENU_ITEMS = [
    { icon: '📋', label: lang === 'es' ? 'Duplicar flujo' : 'Duplicate workflow', action: handleDuplicate },
    { icon: '📤', label: lang === 'es' ? 'Exportar JSON' : 'Export JSON', action: handleExportJSON },
    { icon: '📥', label: lang === 'es' ? 'Importar JSON' : 'Import JSON', action: () => fileInputRef.current?.click() },
    { divider: true },
    { icon: '🔄', label: lang === 'es' ? 'Regenerar con IA' : 'Regenerate with AI', action: handleRegenerate },
    { icon: '📊', label: lang === 'es' ? 'Ver historial' : 'View history', action: handleViewHistory },
    { divider: true },
    { icon: '⚡', label: lang === 'es' ? 'Auto-conectar secuencial' : 'Auto-connect sequential', action: handleAutoConnect },
    { icon: '🎨', label: lang === 'es' ? 'Auto-layout (grid)' : 'Auto-layout (grid)', action: handleAutoLayout },
  ]

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 56px)', overflow: 'hidden', background: '#F9FAFB' }}>

      {/* Hidden file input for import */}
      <input ref={fileInputRef} type="file" accept=".json" style={{ display: 'none' }} onChange={handleImportJSON} />

      {/* Top bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '10px 20px',
        background: '#fff', borderBottom: '1px solid #E5E7EB', flexShrink: 0,
      }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6366F1" strokeWidth="2" strokeLinecap="round">
          <path d="M4 6h16M4 12h8m-8 6h16" />
        </svg>
        <input
          value={workflowName}
          onChange={(e) => setWorkflowName(e.target.value)}
          style={{
            fontSize: 16, fontWeight: 700, color: '#111827', border: 'none',
            outline: 'none', background: 'transparent', minWidth: 200,
          }}
          aria-label="Workflow name"
        />
        <span style={{ fontSize: 12, color: '#9CA3AF', marginLeft: 4 }}>
          {nodes.length} {lang === 'es' ? 'nodos' : 'nodes'} · {edges.length} {lang === 'es' ? 'conexiones' : 'edges'}
        </span>

        {/* Builder menu */}
        <div style={{ position: 'relative', marginLeft: 'auto' }}>
          <button
            onClick={() => setShowBuilderMenu(!showBuilderMenu)}
            style={{
              background: showBuilderMenu ? '#EEF2FF' : 'none', border: '1px solid #E5E7EB',
              borderRadius: 8, padding: '6px 10px', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 13, fontWeight: 600, color: '#6366F1',
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
            </svg>
            {lang === 'es' ? 'Opciones' : 'Options'}
          </button>

          {showBuilderMenu && (
            <div style={{
              position: 'absolute', right: 0, top: 38, width: 220, zIndex: 100,
              background: '#fff', border: '1px solid #E5E7EB', borderRadius: 12,
              boxShadow: '0 8px 32px rgba(0,0,0,0.12)', padding: 4,
            }}>
              {BUILDER_MENU_ITEMS.map((item, i) =>
                item.divider ? (
                  <div key={i} style={{ height: 1, background: '#F3F4F6', margin: '4px 8px' }} />
                ) : (
                  <div
                    key={i}
                    onClick={item.action}
                    style={{
                      padding: '8px 10px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
                      display: 'flex', alignItems: 'center', gap: 8,
                      color: '#374151', transition: 'background 0.15s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F9FAFB'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <span style={{ fontSize: 15 }}>{item.icon}</span>
                    {item.label}
                  </div>
                )
              )}
            </div>
          )}
        </div>
      </div>

      {/* Body: sidebar + canvas */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Left sidebar */}
        <div style={{
          width: 200, flexShrink: 0, background: '#fff',
          borderRight: '1px solid #E5E7EB', display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
        }}>
          <div style={{ padding: '12px 10px 8px', borderBottom: '1px solid #F3F4F6' }}>
            <p style={{ fontSize: 11, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 8 }}>
              {lang === 'es' ? 'Agentes' : 'Agents'} ({agents.length})
            </p>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={lang === 'es' ? 'Buscar...' : 'Search...'}
              style={{
                width: '100%', padding: '5px 8px', borderRadius: 6, fontSize: 12,
                border: '1px solid #E5E7EB', outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px 10px' }}>
            {filteredAgents.length === 0 && (
              <p style={{ fontSize: 12, color: '#9CA3AF', textAlign: 'center', marginTop: 20 }}>
                {agents.length === 0
                  ? (lang === 'es' ? 'Cargando...' : 'Loading...')
                  : (lang === 'es' ? 'Sin resultados' : 'No match')}
              </p>
            )}
            {filteredAgents.map((a) => (
              <SidebarAgent key={a.agent_type} agent={a} onDragStart={handleSidebarDragStart} />
            ))}
          </div>
          <div style={{ padding: '8px 10px', borderTop: '1px solid #F3F4F6', fontSize: 11, color: '#9CA3AF' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#6366F1' }} />
              {lang === 'es' ? 'Arrastra al canvas' : 'Drag to canvas'}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981' }} />
              {lang === 'es' ? 'Puerto entrada (izq.)' : 'Input port (left)'}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#6366F1' }} />
              {lang === 'es' ? 'Puerto salida (der.)' : 'Output port (right)'}
            </div>
          </div>
        </div>

        {/* Canvas */}
        <div
          ref={canvasRef}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleCanvasDrop}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onClick={() => setSelected(null)}
          style={{
            flex: 1, position: 'relative', overflow: 'auto',
            backgroundImage: 'radial-gradient(circle, #D1D5DB 1px, transparent 1px)',
            backgroundSize: '24px 24px',
            cursor: 'default',
          }}
        >
          {nodes.length === 0 && (
            <div style={{
              position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', pointerEvents: 'none',
            }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#D1D5DB" strokeWidth="1.5">
                <path d="M4 6h16M4 12h8m-8 6h16" />
              </svg>
              <p style={{ color: '#9CA3AF', fontSize: 14, marginTop: 12 }}>
                {lang === 'es' ? 'Arrastra agentes aquí para construir tu flujo' : 'Drag agents here to build your workflow'}
              </p>
            </div>
          )}

          {/* SVG layer for edges */}
          <svg
            ref={svgRef}
            style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', overflow: 'visible' }}
          >
            <defs>
              <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L0,6 L8,3 z" fill="#6366F1" />
              </marker>
            </defs>
            {/* Committed edges */}
            {edges.map((e) => {
              const from = nodes.find((n) => n.id === e.from)
              const to = nodes.find((n) => n.id === e.to)
              if (!from || !to) return null
              return (
                <Edge
                  key={`${e.from}-${e.to}`}
                  fromNode={from}
                  toNode={to}
                  onDelete={() => deleteEdge(e.from, e.to)}
                />
              )
            })}
            {/* Pending edge while drawing */}
            {pendingLine && (
              <line
                x1={pendingLine.x1} y1={pendingLine.y1}
                x2={pendingLine.x2} y2={pendingLine.y2}
                stroke="#F59E0B" strokeWidth="2" strokeDasharray="6 3"
                markerEnd="url(#arrow)"
              />
            )}
          </svg>

          {/* Node layer */}
          <svg
            style={{ position: 'absolute', top: 0, left: 0, overflow: 'visible', pointerEvents: 'all' }}
            width="100%" height="100%"
          >
            {nodes.map((node) => (
              <AgentNode
                key={node.id}
                node={node}
                selected={selected === node.id}
                connecting={connectingFrom.current === node.id}
                onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                onDelete={(e) => { e.stopPropagation(); deleteNode(node.id) }}
                onPortMouseDown={handlePortMouseDown}
                onPortMouseUp={handlePortMouseUp}
              />
            ))}
          </svg>
        </div>

        {/* Right panel — selected node details */}
        {selected && (() => {
          const node = nodes.find((n) => n.id === selected)
          if (!node) return null
          const deps = edges.filter((e) => e.to === node.id).map((e) => nodes.find((n) => n.id === e.from)?.name).filter(Boolean)
          return (
            <div style={{
              width: 220, flexShrink: 0, background: '#fff',
              borderLeft: '1px solid #E5E7EB', padding: 16, overflowY: 'auto',
            }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 12 }}>
                {lang === 'es' ? 'Propiedades del nodo' : 'Node Properties'}
              </p>
              <label style={{ fontSize: 12, color: '#6B7280', display: 'block', marginBottom: 4 }}>
                {lang === 'es' ? 'Nombre del paso' : 'Step name'}
              </label>
              <input
                value={node.name}
                onChange={(e) => setNodes((prev) => prev.map((n) => n.id === node.id ? { ...n, name: e.target.value } : n))}
                style={{
                  width: '100%', padding: '6px 8px', borderRadius: 6, fontSize: 12,
                  border: '1px solid #E5E7EB', outline: 'none', boxSizing: 'border-box', marginBottom: 12,
                }}
              />
              <label style={{ fontSize: 12, color: '#6B7280', display: 'block', marginBottom: 4 }}>
                {lang === 'es' ? 'Tipo de agente' : 'Agent type'}
              </label>
              <div style={{
                padding: '6px 8px', borderRadius: 6, fontSize: 12, fontFamily: 'monospace',
                background: agentColor(node.agent_type) + '18', color: agentColor(node.agent_type),
                fontWeight: 700, marginBottom: 12,
              }}>
                {node.agent_type}
              </div>
              <label style={{ fontSize: 12, color: '#6B7280', display: 'block', marginBottom: 4 }}>
                {lang === 'es' ? 'Depende de' : 'Depends on'}
              </label>
              {deps.length === 0
                ? <p style={{ fontSize: 12, color: '#9CA3AF' }}>{lang === 'es' ? 'Sin dependencias' : 'No dependencies'}</p>
                : deps.map((d) => (
                  <div key={d} style={{
                    fontSize: 12, padding: '3px 8px', borderRadius: 4, background: '#EEF2FF',
                    color: '#6366F1', marginBottom: 4, fontFamily: 'monospace',
                  }}>{d}</div>
                ))
              }
              <button
                onClick={() => deleteNode(node.id)}
                style={{
                  marginTop: 16, width: '100%', padding: '7px', borderRadius: 6,
                  border: '1px solid #FCA5A5', background: '#FEF2F2', color: '#EF4444',
                  fontSize: 12, fontWeight: 600, cursor: 'pointer',
                }}
              >
                {lang === 'es' ? 'Eliminar nodo' : 'Delete Node'}
              </button>
            </div>
          )
        })()}
      </div>

      {/* Bottom toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '10px 20px',
        background: '#fff', borderTop: '1px solid #E5E7EB', flexShrink: 0,
      }}>
        <button
          onClick={clearCanvas}
          style={{
            padding: '8px 14px', borderRadius: 7, border: '1px solid #E5E7EB',
            background: '#F9FAFB', color: '#6B7280', fontSize: 13, cursor: 'pointer',
          }}
        >
          {lang === 'es' ? 'Limpiar' : 'Clear'}
        </button>
        <div style={{ flex: 1 }} />
        {/* DAG preview */}
        <span style={{ fontSize: 12, color: '#9CA3AF', fontFamily: 'monospace' }}>
          {nodes.length} {lang === 'es' ? 'pasos' : 'steps'} · {edges.length} {lang === 'es' ? 'conexiones' : 'edges'}
        </span>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: '8px 18px', borderRadius: 7, border: 'none',
            background: saving ? '#A5B4FC' : '#6366F1', color: '#fff',
            fontSize: 13, fontWeight: 600, cursor: saving ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          {saving ? (lang === 'es' ? 'Guardando…' : 'Saving…') : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" /><polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" />
              </svg>
              {lang === 'es' ? 'Guardar flujo' : 'Save Workflow'}
            </>
          )}
        </button>
        <button
          onClick={handleExecute}
          disabled={executing}
          style={{
            padding: '8px 18px', borderRadius: 7, border: 'none',
            background: executing ? '#6EE7B7' : '#059669', color: '#fff',
            fontSize: 13, fontWeight: 600, cursor: executing ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          {executing ? (lang === 'es' ? 'Ejecutando…' : 'Running…') : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              {lang === 'es' ? 'Ejecutar' : 'Execute'}
            </>
          )}
        </button>
      </div>

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 80, right: 24, zIndex: 9999,
          padding: '10px 18px', borderRadius: 8, fontSize: 13, fontWeight: 500,
          background: toast.type === 'error' ? '#FEF2F2' : '#F0FDF4',
          color: toast.type === 'error' ? '#DC2626' : '#16A34A',
          border: `1px solid ${toast.type === 'error' ? '#FECACA' : '#BBF7D0'}`,
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          animation: 'fadeIn 0.2s ease-out',
        }}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
