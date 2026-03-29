import { useState } from 'react'

const STEPS = {
  es: [
    {
      icon: '{ }',
      title: 'NexusForge AI',
      description: 'Plataforma de Orquestación Multi-Agente Empresarial. Coordina 22 agentes IA especializados a través de 6 topologías de ejecución con memoria de 3 niveles, auto-reparación y observabilidad completa. Construida con FastAPI, React 18 y respaldada por PostgreSQL, Redis y pgvector.',
    },
    {
      icon: 'DAG',
      title: 'Ejecución de Workflows',
      description: 'Define flujos de trabajo como Grafos Acíclicos Dirigidos (DAGs) que encadenan agentes especializados. Elige entre 6 topologías de enjambre — secuencial, paralelo, jerárquico, debate, consenso y adaptivo — según tu caso de uso. El motor DAG usa el algoritmo de Kahn para ordenamiento topológico con ejecución paralela automática.',
    },
    {
      icon: 'MEM',
      title: 'Arquitectura de Memoria',
      description: 'Sistema de 3 niveles: Memoria de Trabajo (en proceso, sub-milisegundo), Memoria Episódica (Redis, TTL 30 días, aprende de ejecuciones pasadas) y Memoria Semántica (pgvector, permanente, vectores de 512 dimensiones). El intercambio de conocimiento entre agentes permite decisiones más inteligentes con el tiempo.',
    },
    {
      icon: 'RLB',
      title: 'Confiabilidad',
      description: 'Auto-reparación con 5 estrategias: Reintento con backoff exponencial, Omitir con salida por defecto, Reparar vía el Agente de Reparación, Escalar a revisión humana y Respaldo desde caché. Cada fallo es detectado, clasificado en 6 tipos y recuperado automáticamente. Circuit breaker entre proveedores LLM.',
    },
    {
      icon: 'OBS',
      title: 'Observabilidad',
      description: 'Timeline tipo LangSmith con trazas paso a paso de cada ejecución. Iconos de estado: éxito, reintento, fallback y fallo. Detalle expandible por paso: entrada/salida, tokens (entrada y salida), latencia en ms, costo en USD y proveedor LLM. Actualizaciones en tiempo real vía WebSocket mientras los workflows se ejecutan.',
    },
    {
      icon: 'EVL',
      title: 'Evaluación',
      description: '16 escenarios de evaluación distribuidos en 3 suites: Operaciones Empresariales (6), Inteligencia Documental (5) y Copiloto de Portafolio (5). Métricas de calidad (0-100), latencia (p50/p95/p99), uso de tokens, costo por escenario, tasa de éxito y conteos de reintentos/fallbacks. Comparación lado a lado entre ejecuciones.',
    },
    {
      icon: 'OPS',
      title: 'Caso Real: Operaciones Empresariales',
      description: '8 agentes especializados procesan solicitudes de clientes: IntakeAgent normaliza, IntentClassifierAgent clasifica la intención, CustomerContextAgent recupera historial, DocumentRAGAgent busca en documentos, SchedulerAgent reprograma citas, CRMUpdateAgent actualiza el CRM, NotificationAgent envía confirmaciones y SupervisorAgent orquesta todo. Bilingüe ES/EN.',
    },
    {
      icon: 'DOC',
      title: 'Caso Real: Inteligencia Documental',
      description: '7 agentes clasifican, extraen y validan documentos de extremo a extremo: DocumentIngestionAgent recibe y normaliza, DocumentClassifierAgent clasifica (contrato, factura, currículum, política, informe), SchemaExtractionAgent extrae campos estructurados, ValidationAgent valida contra reglas de negocio, SummaryAgent genera resumen, StorageAgent almacena en la base de conocimiento y SupervisorAgent coordina.',
    },
    {
      icon: 'CPL',
      title: 'Caso Real: Copiloto de Portafolio',
      description: '6 agentes responden preguntas sobre proyectos y habilidades: RouterAgent analiza y enruta la pregunta, PortfolioRAGAgent recupera información relevante, ProjectComparisonAgent compara proyectos, SkillsMapperAgent mapea habilidades y niveles de expertise, ResponseFormatterAgent formatea la respuesta con markdown enriquecido y SupervisorAgent asegura la calidad.',
    },
    {
      icon: 'PLY',
      title: 'Playground Interactivo',
      description: 'Ejecuta workflows en tiempo real desde la interfaz. 3 workflows disponibles: Operaciones Empresariales, Inteligencia Documental y Copiloto de Portafolio. Visualiza el timeline de agentes paso a paso, resultados estructurados finales y métricas de tokens, costo y latencia. Funciona tanto en modo Demo como en modo Real.',
    },
    {
      icon: 'CST',
      title: 'Métricas de Costos',
      description: 'Tracking completo de tokens, costos y rendimiento por agente. Uso de tokens por ejecución y por agente, costos en USD (Groq: $0.59/$0.79 por M tokens, Claude: $3/$15 por M tokens), tasa de éxito, conteo de reintentos y fallbacks. Gráficos de tendencias, barras por agente y distribución por proveedor LLM.',
    },
    {
      icon: 'GO',
      title: 'Cómo Empezar',
      description: 'Explora el Dashboard para ver el estado del sistema. Usa el Playground para ejecutar los 3 workflows interactivamente. Revisa el Timeline para entender la ejecución paso a paso. Consulta el Dashboard de Costos para monitorear tokens y gastos. Cambia entre modo Demo (sin backend) y modo Real (con FastAPI) desde Configuración. El Asistente IA siempre está disponible.',
    },
  ],
  en: [
    {
      icon: '{ }',
      title: 'NexusForge AI',
      description: 'Enterprise Multi-Agent Orchestration Platform. Coordinates 22 specialized AI agents across 6 execution topologies with 3-tier memory, self-healing, and full observability. Built with FastAPI, React 18, backed by PostgreSQL, Redis, and pgvector.',
    },
    {
      icon: 'DAG',
      title: 'Workflow Execution',
      description: 'Define workflows as Directed Acyclic Graphs (DAGs) that chain specialized agents. Choose from 6 swarm topologies — sequential, parallel, hierarchical, debate, consensus, and adaptive — to match your use case. The DAG engine uses Kahn\'s algorithm for topological sorting with automatic parallel execution.',
    },
    {
      icon: 'MEM',
      title: 'Memory Architecture',
      description: '3-tier system: Working Memory (in-process, sub-millisecond), Episodic Memory (Redis, 30-day TTL, learns from past executions), and Semantic Memory (pgvector, permanent, 512-dimensional vectors). Cross-agent knowledge sharing enables smarter decisions over time.',
    },
    {
      icon: 'RLB',
      title: 'Reliability',
      description: 'Self-healing with 5 strategies: Retry with exponential backoff, Skip with default output, Repair via the Repair Agent, Escalate to human review, and Fallback from cache. Every failure is detected, classified into 6 types, and recovered automatically. Circuit breaker between LLM providers.',
    },
    {
      icon: 'OBS',
      title: 'Observability',
      description: 'LangSmith-style timeline with step-by-step traces for every execution. Status icons: success, retry, fallback, and failure. Expandable detail per step: input/output, tokens (input and output), latency in ms, cost in USD, and LLM provider. Real-time updates via WebSocket as workflows execute.',
    },
    {
      icon: 'EVL',
      title: 'Evaluation',
      description: '16 evaluation scenarios across 3 suites: Enterprise Operations (6), Document Intelligence (5), and Portfolio Copilot (5). Quality scoring (0-100), latency metrics (p50/p95/p99), token usage, cost per scenario, success rate, and retry/fallback counts. Side-by-side run comparisons.',
    },
    {
      icon: 'OPS',
      title: 'Use Case: Enterprise Operations Assistant',
      description: '8 specialized agents process customer requests: IntakeAgent normalizes, IntentClassifierAgent classifies intent, CustomerContextAgent retrieves history, DocumentRAGAgent searches documents, SchedulerAgent reschedules meetings, CRMUpdateAgent updates CRM, NotificationAgent sends confirmations, and SupervisorAgent orchestrates the flow. Bilingual ES/EN.',
    },
    {
      icon: 'DOC',
      title: 'Use Case: Document Intelligence',
      description: '7 agents classify, extract, and validate documents end-to-end: DocumentIngestionAgent receives and normalizes, DocumentClassifierAgent classifies (contract, invoice, resume, policy, report), SchemaExtractionAgent extracts structured fields, ValidationAgent validates against business rules, SummaryAgent generates summary, StorageAgent stores in knowledge base, and SupervisorAgent coordinates.',
    },
    {
      icon: 'CPL',
      title: 'Use Case: Portfolio Copilot',
      description: '6 agents answer questions about projects and skills: RouterAgent analyzes and routes the question, PortfolioRAGAgent retrieves relevant information, ProjectComparisonAgent compares projects, SkillsMapperAgent maps skills and expertise levels, ResponseFormatterAgent formats with rich markdown, and SupervisorAgent ensures quality.',
    },
    {
      icon: 'PLY',
      title: 'Interactive Playground',
      description: 'Execute workflows in real-time from the interface. 3 workflows available: Enterprise Operations, Document Intelligence, and Portfolio Copilot. Watch the agent timeline step by step, view structured final results, and track token, cost, and latency metrics. Works in both Demo and Real mode.',
    },
    {
      icon: 'CST',
      title: 'Cost Metrics',
      description: 'Comprehensive token, cost, and performance tracking per agent. Token usage per run and per agent, costs in USD (Groq: $0.59/$0.79 per M tokens, Claude: $3/$15 per M tokens), success rate, retry count, and fallback count. Trend line charts, per-agent bar charts, and LLM provider distribution.',
    },
    {
      icon: 'GO',
      title: 'Getting Started',
      description: 'Explore the Dashboard for system health at a glance. Use the Playground to run all 3 workflows interactively. Check the Timeline to understand step-by-step execution. Monitor the Cost Dashboard for tokens and spending. Switch between Demo mode (no backend) and Real mode (with FastAPI) in Settings. The AI Assistant is always available.',
    },
  ],
}

export default function Onboarding({ lang = 'es', onDismiss }) {
  const [dismissed, setDismissed] = useState(false)
  const currentLang = lang === 'en' ? 'en' : 'es'
  const steps = STEPS[currentLang]

  if (dismissed) return null

  const handleDismiss = () => {
    setDismissed(true)
    if (onDismiss) onDismiss()
  }

  return (
    <div style={{ padding: '0 0 32px', animation: 'fadeIn 0.4s ease-out' }}>
      {/* Hero */}
      <div className="nxf-onboarding-hero" style={{
        textAlign: 'center', padding: '48px 24px 40px', marginBottom: 32,
        background: '#FFFFFF', borderRadius: 16, border: '1px solid #E5E7EB',
        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          padding: '6px 16px', borderRadius: 100,
          background: 'rgba(37,99,235,0.06)', color: '#2563EB',
          fontSize: 13, fontWeight: 600, marginBottom: 20,
          border: '1px solid rgba(37,99,235,0.12)',
        }}>
          NexusForge AI Platform
        </div>
        <h1 style={{
          fontSize: 32, fontWeight: 700, color: '#111827',
          lineHeight: 1.2, marginBottom: 12, letterSpacing: '-0.02em',
        }}>
          {currentLang === 'es'
            ? 'Plataforma de Orquestación Multi-Agente Empresarial'
            : 'Enterprise Multi-Agent Orchestration Platform'}
        </h1>
        <p style={{
          fontSize: 16, color: '#4B5563', maxWidth: 640,
          margin: '0 auto', lineHeight: 1.6,
        }}>
          {currentLang === 'es'
            ? 'Ejecución de workflows de IA observable, resiliente y extensible. 22 agentes, 6 topologías, memoria de 3 niveles, auto-reparación, 3 casos de uso reales, Playground interactivo y evaluación con 16 escenarios.'
            : 'Observable, resilient, and extensible AI workflow execution. 22 agents, 6 topologies, 3-tier memory, self-healing, 3 real use cases, interactive Playground, and evaluation with 16 scenarios.'}
        </p>
      </div>

      {/* Step Cards */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(320px, 100%), 1fr))',
        gap: 16, marginBottom: 24,
      }}>
        {steps.map((step, i) => (
          <div key={i} style={{
            background: '#FFFFFF', border: '1px solid #E5E7EB',
            borderRadius: 12, padding: '24px 24px 20px',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            transition: 'box-shadow 0.2s, border-color 0.2s',
          }}
            onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.06)'; e.currentTarget.style.borderColor = 'rgba(37,99,235,0.3)' }}
            onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 1px 2px rgba(0,0,0,0.04)'; e.currentTarget.style.borderColor = '#E5E7EB' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: 'rgba(37,99,235,0.06)', display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                color: '#2563EB', fontWeight: 700, fontSize: 12,
                fontFamily: 'monospace', border: '1px solid rgba(37,99,235,0.12)',
                flexShrink: 0,
              }}>{step.icon}</div>
              <div style={{
                fontSize: 11, fontWeight: 600, color: '#9CA3AF',
                textTransform: 'uppercase', letterSpacing: '0.06em',
              }}>
                {currentLang === 'es' ? `Paso ${i + 1} de ${steps.length}` : `Step ${i + 1} of ${steps.length}`}
              </div>
            </div>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: '#111827', marginBottom: 8, lineHeight: 1.4 }}>
              {step.title}
            </h3>
            <p style={{ fontSize: 14, color: '#4B5563', lineHeight: 1.6 }}>
              {step.description}
            </p>
          </div>
        ))}
      </div>

      {/* Dismiss */}
      <div style={{ textAlign: 'center' }}>
        <button onClick={handleDismiss} style={{
          padding: '10px 28px', borderRadius: 8, border: 'none',
          background: '#2563EB', color: '#FFFFFF',
          fontSize: 14, fontWeight: 600, cursor: 'pointer',
          transition: 'background 0.15s',
        }}
          onMouseEnter={e => e.currentTarget.style.background = '#1D4ED8'}
          onMouseLeave={e => e.currentTarget.style.background = '#2563EB'}
        >
          {currentLang === 'es' ? 'Ir al Dashboard' : 'Go to Dashboard'}
        </button>
      </div>
    </div>
  )
}
