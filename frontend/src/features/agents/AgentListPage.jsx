import { useState, useEffect } from 'react'
import { t } from '../../shared/i18n/translations'
import AgentCard from './AgentCard'
import AgentDetailPanel from './AgentDetailPanel'

const DEMO_AGENTS = [
  {
    id: 'agent-1', name: 'DocClassifier', type: 'classifier', status: 'active',
    description: 'Clasifica documentos entrantes por tipo (legal, financiero, técnico) usando análisis semántico avanzado con LLMs.',
    tools: ['classify', 'embeddings', 'confidence_score'],
    system_prompt: 'You are a document classifier. Analyze the document content and classify it into one of the predefined categories.',
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.1, max_tokens: 500 },
    stats: { total_runs: 1247, avg_duration: 3200, success_rate: 0.96 },
  },
  {
    id: 'agent-2', name: 'EntityExtractor', type: 'extractor', status: 'active',
    description: 'Extrae entidades nombradas, fechas, montos y relaciones de documentos clasificados.',
    tools: ['ner', 'date_parser', 'amount_parser', 'relation_map'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.0, max_tokens: 2000 },
    stats: { total_runs: 983, avg_duration: 5100, success_rate: 0.92 },
  },
  {
    id: 'agent-3', name: 'SummaryAgent', type: 'summarizer', status: 'active',
    description: 'Genera resumenes ejecutivos concisos de documentos largos manteniendo puntos clave.',
    tools: ['summarize', 'key_points', 'action_items'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.3, max_tokens: 1500 },
    stats: { total_runs: 654, avg_duration: 4300, success_rate: 0.98 },
  },
  {
    id: 'agent-4', name: 'ContentGen', type: 'generator', status: 'active',
    description: 'Genera contenido nuevo basado en templates y datos estructurados extraídos previamente.',
    tools: ['generate', 'template_fill', 'tone_adjust'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.7, max_tokens: 3000 },
    stats: { total_runs: 421, avg_duration: 6200, success_rate: 0.94 },
  },
  {
    id: 'agent-5', name: 'FlowRouter', type: 'router', status: 'active',
    description: 'Decide que agente debe procesar cada paso del workflow basándose en el contexto actual.',
    tools: ['route', 'evaluate_context', 'select_agent'],
    config: { model: 'claude-haiku-4-20250414', temperature: 0.0, max_tokens: 200 },
    stats: { total_runs: 2105, avg_duration: 800, success_rate: 0.99 },
  },
  {
    id: 'agent-6', name: 'DataValidator', type: 'validator', status: 'active',
    description: 'Valida la calidad y consistencia de datos extraídos antes de almacenarlos en el sistema.',
    tools: ['validate_schema', 'check_consistency', 'quality_score'],
    config: { model: 'claude-haiku-4-20250414', temperature: 0.0, max_tokens: 500 },
    stats: { total_runs: 789, avg_duration: 1200, success_rate: 0.97 },
  },
  {
    id: 'agent-7', name: 'SentimentAnalyzer', type: 'analyzer', status: 'active',
    description: 'Analiza el sentimiento y tono emocional de textos, reviews y comunicaciones de clientes.',
    tools: ['sentiment_score', 'emotion_detect', 'tone_classify'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.1, max_tokens: 800 },
    stats: { total_runs: 1532, avg_duration: 2100, success_rate: 0.95 },
  },
  {
    id: 'agent-8', name: 'TranslationAgent', type: 'translator', status: 'active',
    description: 'Traduce documentos entre idiomas manteniendo contexto técnico y formato original.',
    tools: ['translate', 'detect_language', 'glossary_lookup'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.2, max_tokens: 4000 },
    stats: { total_runs: 876, avg_duration: 4800, success_rate: 0.93 },
  },
  {
    id: 'agent-9', name: 'CodeReviewer', type: 'reviewer', status: 'active',
    description: 'Revisa código fuente buscando bugs, vulnerabilidades y oportunidades de mejora.',
    tools: ['lint', 'security_scan', 'suggest_fix', 'complexity_check'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.1, max_tokens: 3000 },
    stats: { total_runs: 445, avg_duration: 7200, success_rate: 0.91 },
  },
  {
    id: 'agent-10', name: 'TestGenerator', type: 'generator', status: 'active',
    description: 'Genera tests unitarios y de integración automáticamente a partir del código fuente.',
    tools: ['generate_unit', 'generate_integration', 'coverage_analysis'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.4, max_tokens: 4000 },
    stats: { total_runs: 312, avg_duration: 8100, success_rate: 0.89 },
  },
  {
    id: 'agent-11', name: 'APIMapper', type: 'mapper', status: 'active',
    description: 'Mapea y documenta endpoints de APIs, genera schemas OpenAPI y cliente SDK.',
    tools: ['map_endpoints', 'generate_schema', 'sdk_generate'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.2, max_tokens: 5000 },
    stats: { total_runs: 198, avg_duration: 6500, success_rate: 0.94 },
  },
  {
    id: 'agent-12', name: 'SchemaValidator', type: 'validator', status: 'active',
    description: 'Valida datos contra schemas JSON/XML y sugiere correcciones automáticas.',
    tools: ['validate_json', 'validate_xml', 'auto_fix_schema'],
    config: { model: 'claude-haiku-4-20250414', temperature: 0.0, max_tokens: 1000 },
    stats: { total_runs: 1876, avg_duration: 900, success_rate: 0.98 },
  },
  {
    id: 'agent-13', name: 'DataTransformer', type: 'transformer', status: 'active',
    description: 'Transforma datos entre formatos (CSV, JSON, XML, Parquet) con mapeo inteligente de campos.',
    tools: ['transform', 'field_map', 'type_cast', 'normalize'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.1, max_tokens: 2000 },
    stats: { total_runs: 654, avg_duration: 3400, success_rate: 0.96 },
  },
  {
    id: 'agent-14', name: 'ReportBuilder', type: 'generator', status: 'active',
    description: 'Construye reportes ejecutivos combinando datos, gráficos y narrativa automatizada.',
    tools: ['build_report', 'chart_generate', 'narrative_write'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.5, max_tokens: 6000 },
    stats: { total_runs: 287, avg_duration: 9200, success_rate: 0.93 },
  },
  {
    id: 'agent-15', name: 'AlertMonitor', type: 'monitor', status: 'active',
    description: 'Monitorea métricas del sistema y genera alertas cuando se detectan anomalías.',
    tools: ['check_metrics', 'threshold_eval', 'send_alert'],
    config: { model: 'claude-haiku-4-20250414', temperature: 0.0, max_tokens: 300 },
    stats: { total_runs: 5432, avg_duration: 400, success_rate: 0.99 },
  },
  {
    id: 'agent-16', name: 'ComplianceChecker', type: 'checker', status: 'active',
    description: 'Verifica que documentos y procesos cumplan con regulaciones (GDPR, SOX, HIPAA).',
    tools: ['check_gdpr', 'check_sox', 'check_hipaa', 'compliance_report'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.0, max_tokens: 2500 },
    stats: { total_runs: 567, avg_duration: 5600, success_rate: 0.97 },
  },
  {
    id: 'agent-17', name: 'PriorityRanker', type: 'ranker', status: 'active',
    description: 'Rankea y prioriza tareas, tickets o documentos según criterios configurables.',
    tools: ['rank', 'score', 'prioritize', 'reorder'],
    config: { model: 'claude-haiku-4-20250414', temperature: 0.1, max_tokens: 600 },
    stats: { total_runs: 2341, avg_duration: 700, success_rate: 0.96 },
  },
  {
    id: 'agent-18', name: 'DuplicateDetector', type: 'detector', status: 'active',
    description: 'Detecta documentos duplicados o quasi-duplicados usando hashing y similitud semántica.',
    tools: ['hash_compare', 'semantic_sim', 'dedup_suggest'],
    config: { model: 'claude-haiku-4-20250414', temperature: 0.0, max_tokens: 500 },
    stats: { total_runs: 1123, avg_duration: 1800, success_rate: 0.94 },
  },
  {
    id: 'agent-19', name: 'ContextLinker', type: 'linker', status: 'active',
    description: 'Enlaza documentos relacionados creando un grafo de conocimiento contextual.',
    tools: ['find_related', 'build_graph', 'suggest_links'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.2, max_tokens: 1500 },
    stats: { total_runs: 432, avg_duration: 4100, success_rate: 0.91 },
  },
  {
    id: 'agent-20', name: 'AnomalyDetector', type: 'detector', status: 'active',
    description: 'Detecta patrones anómalos en datos financieros, logs y series temporales.',
    tools: ['detect_anomaly', 'statistical_test', 'pattern_match'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.0, max_tokens: 1000 },
    stats: { total_runs: 3210, avg_duration: 1500, success_rate: 0.95 },
  },
  {
    id: 'agent-21', name: 'FeedbackCollector', type: 'collector', status: 'active',
    description: 'Recopila y estructura feedback de usuarios, encuestas y evaluaciones de calidad.',
    tools: ['collect', 'structure', 'aggregate', 'trend_analyze'],
    config: { model: 'claude-haiku-4-20250414', temperature: 0.1, max_tokens: 800 },
    stats: { total_runs: 876, avg_duration: 1100, success_rate: 0.97 },
  },
  {
    id: 'agent-22', name: 'QualityAssurer', type: 'assurer', status: 'active',
    description: 'Ejecuta checks de calidad end-to-end en outputs de otros agentes antes de entregar.',
    tools: ['qa_check', 'consistency_verify', 'format_validate', 'final_score'],
    config: { model: 'claude-sonnet-4-20250514', temperature: 0.0, max_tokens: 1500 },
    stats: { total_runs: 1654, avg_duration: 2200, success_rate: 0.98 },
  },
]

export default function AgentListPage({ lang = 'en' }) {
  const [agents] = useState(DEMO_AGENTS)
  const [selected, setSelected] = useState(null)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          {t('agents', lang)}
        </h1>
        <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
          {t('manageAgents', lang)}
          <span style={{ marginLeft: 8, color: '#6366F1' }}>{agents.length} {t('registered', lang)}</span>
        </p>
      </div>

      <div data-tour="agent-grid" style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: 16, marginBottom: 24,
      }}>
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
