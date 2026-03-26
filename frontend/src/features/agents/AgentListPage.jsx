import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import AgentCard from './AgentCard'
import AgentDetailPanel from './AgentDetailPanel'

const DEMO_AGENTS = [
  {
    id: 'agent-1', name: 'DocClassifier', type: 'classifier', status: 'active',
    description: 'Clasifica documentos entrantes por tipo (legal, financiero, tecnico) usando analisis semantico avanzado con LLMs.',
    tools: ['classify', 'embeddings', 'confidence_score'],
    system_prompt: 'You are a document classifier. Analyze the document content and classify it into one of the predefined categories. Return the category and confidence score.',
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.1, max_tokens: 500 },
    stats: { total_runs: 1247, avg_duration: 3200, success_rate: 0.96 },
  },
  {
    id: 'agent-2', name: 'EntityExtractor', type: 'extractor', status: 'active',
    description: 'Extrae entidades nombradas, fechas, montos y relaciones de documentos clasificados.',
    tools: ['ner', 'date_parser', 'amount_parser', 'relation_map'],
    system_prompt: 'You are an entity extraction agent. Extract all named entities, dates, monetary amounts, and relationships from the provided text.',
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.0, max_tokens: 2000 },
    stats: { total_runs: 983, avg_duration: 5100, success_rate: 0.92 },
  },
  {
    id: 'agent-3', name: 'SummaryAgent', type: 'summarizer', status: 'active',
    description: 'Genera resumenes ejecutivos concisos de documentos largos manteniendo puntos clave.',
    tools: ['summarize', 'key_points', 'action_items'],
    system_prompt: 'You are a summarization agent. Create concise executive summaries that capture the key points and action items.',
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.3, max_tokens: 1500 },
    stats: { total_runs: 654, avg_duration: 4300, success_rate: 0.98 },
  },
  {
    id: 'agent-4', name: 'ContentGen', type: 'generator', status: 'active',
    description: 'Genera contenido nuevo basado en templates y datos estructurados extraidos previamente.',
    tools: ['generate', 'template_fill', 'tone_adjust'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.7, max_tokens: 3000 },
    stats: { total_runs: 421, avg_duration: 6200, success_rate: 0.94 },
  },
  {
    id: 'agent-5', name: 'FlowRouter', type: 'router', status: 'active',
    description: 'Decide que agente debe procesar cada paso del workflow basandose en el contexto actual.',
    tools: ['route', 'evaluate_context', 'select_agent'],
    config: { model: 'claude-haiku-4-20250414', temperature: 0.0, max_tokens: 200 },
    stats: { total_runs: 2105, avg_duration: 800, success_rate: 0.99 },
  },
  {
    id: 'agent-6', name: 'DataValidator', type: 'validator', status: 'paused',
    description: 'Valida la calidad y consistencia de datos extraidos antes de almacenarlos en el sistema.',
    tools: ['validate_schema', 'check_consistency', 'quality_score'],
    config: { model: 'claude-haiku-4-20250414', temperature: 0.0, max_tokens: 500 },
    stats: { total_runs: 789, avg_duration: 1200, success_rate: 0.97 },
  },
]

export default function AgentListPage() {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    async function load() {
      try {
        const data = await api.get('/agents')
        setAgents(Array.isArray(data) ? data : data.items || DEMO_AGENTS)
      } catch {
        setAgents(DEMO_AGENTS)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 8 }}>Agentes</h1>
        <p style={{ fontSize: 14, color: '#9CA3AF' }}>Cargando agentes...</p>
      </div>
    )
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 4 }}>Agentes</h1>
        <p style={{ fontSize: 14, color: '#9CA3AF' }}>
          Gestiona y configura los agentes IA disponibles.
          <span style={{ marginLeft: 8, color: '#6366F1' }}>{agents.length} registrados</span>
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16, marginBottom: 24 }}>
        {agents.map((agent) => (
          <AgentCard
            key={agent.id}
            agent={agent}
            selected={selected?.id === agent.id}
            onClick={(a) => setSelected(selected?.id === a.id ? null : a)}
          />
        ))}
      </div>

      {selected && (
        <AgentDetailPanel agent={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}
