import { useState } from 'react'

const STEPS = {
  es: [
    {
      icon: '{ }',
      title: 'NexusForge AI: Plataforma de Orquestación Multi-Agente',
      description: 'Plataforma de grado empresarial para orquestar agentes IA autónomos a escala. Construye, despliega y monitorea flujos de trabajo inteligentes con observabilidad completa y confiabilidad enterprise.',
    },
    {
      icon: 'DAG',
      title: 'Ejecución de Workflows: DAG + Swarm',
      description: 'Define flujos de trabajo como Grafos Acíclicos Dirigidos (DAGs) que encadenan agentes especializados. Elige entre 6 topologías de enjambre — secuencial, paralelo, jerárquico, debate, consenso y adaptativo — según tu caso de uso.',
    },
    {
      icon: 'MEM',
      title: 'Arquitectura de Memoria: Sistema de 3 Niveles',
      description: 'Los agentes comparten contexto a través de Memoria de Trabajo (en proceso), Memoria Episódica (Redis, TTL 30 días) y Memoria Semántica (pgvector, permanente). El intercambio de conocimiento entre agentes permite decisiones más inteligentes.',
    },
    {
      icon: 'RLB',
      title: 'Confiabilidad: Diseñado para Producción',
      description: 'Reintentos automáticos con backoff exponencial, cadenas de fallback inteligentes, circuit breakers y checkpoints de ejecución. Cada fallo es detectado, clasificado y recuperado usando 5 estrategias de auto-reparación.',
    },
    {
      icon: 'OBS',
      title: 'Observabilidad: Visibilidad Total de Ejecución',
      description: 'Vistas de timeline en tiempo real, trazas de ejecución paso a paso, métricas de latencia, uso de tokens y tracking de costos. El streaming WebSocket entrega actualizaciones en vivo mientras los workflows se ejecutan.',
    },
    {
      icon: 'EVL',
      title: 'Evaluación: Medir lo que Importa',
      description: 'Ejecuta escenarios de evaluación para medir el rendimiento de agentes. Rastrea tasas de éxito, latencia promedio, conteo de fallbacks y costo por ejecución en toda tu flota de agentes.',
    },
    {
      icon: 'OPS',
      title: 'Caso de Uso: Asistente de Operaciones Empresariales',
      description: '8 agentes especializados procesan solicitudes de clientes: clasificación de intención, consulta de documentos, reprogramación de citas, actualización de CRM y generación de respuestas. Un caso real ejecutándose sobre el motor NexusForge.',
    },
    {
      icon: 'GO',
      title: 'Cómo Empezar',
      description: 'Explora el Dashboard para ver el estado del sistema. Usa Workflows para construir pipelines. Monitorea Ejecuciones en tiempo real. El Asistente IA está siempre disponible para responder preguntas.',
    },
  ],
  en: [
    {
      icon: '{ }',
      title: 'NexusForge AI: Enterprise Multi-Agent Orchestration Platform',
      description: 'A production-grade platform for orchestrating autonomous AI agents at scale. Build, deploy, and monitor intelligent workflows with full observability and enterprise reliability.',
    },
    {
      icon: 'DAG',
      title: 'Workflow Execution: DAG + Swarm',
      description: 'Define workflows as Directed Acyclic Graphs (DAGs) that chain specialized agents. Choose from 6 swarm topologies — sequential, parallel, hierarchical, debate, consensus, and adaptive — to match your use case.',
    },
    {
      icon: 'MEM',
      title: 'Memory Architecture: 3-Tier System',
      description: 'Agents share context through Working Memory (in-process), Episodic Memory (Redis, 30-day TTL), and Semantic Memory (pgvector, permanent). Cross-agent knowledge sharing enables smarter decisions over time.',
    },
    {
      icon: 'RLB',
      title: 'Reliability: Built for Production',
      description: 'Automatic retries with exponential backoff, intelligent fallback chains, circuit breakers, and execution checkpoints. Every failure is detected, classified, and recovered from using 5 healing strategies.',
    },
    {
      icon: 'OBS',
      title: 'Observability: Full Execution Visibility',
      description: 'Real-time timeline views, step-by-step execution traces, latency metrics, token usage, and cost tracking. WebSocket streaming delivers live updates as workflows execute.',
    },
    {
      icon: 'EVL',
      title: 'Evaluation: Measure What Matters',
      description: 'Run evaluation scenarios to benchmark agent performance. Track success rates, average latency, fallback counts, and cost per execution across your entire agent fleet.',
    },
    {
      icon: 'OPS',
      title: 'Use Case: Enterprise Operations Assistant',
      description: '8 specialized agents process customer requests: intent classification, document lookup, meeting rescheduling, CRM updates, and response generation. A real use case running on the NexusForge engine.',
    },
    {
      icon: 'GO',
      title: 'Getting Started',
      description: 'Explore the Dashboard for system health at a glance. Use Workflows to build pipelines. Monitor Executions in real-time. The AI Assistant is always available to answer questions.',
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
      <div style={{
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
            ? 'Plataforma de Orquestación Multi-Agente'
            : 'Enterprise Multi-Agent Orchestration Platform'}
        </h1>
        <p style={{
          fontSize: 16, color: '#4B5563', maxWidth: 560,
          margin: '0 auto', lineHeight: 1.6,
        }}>
          {currentLang === 'es'
            ? 'Ejecución de workflows de IA observable, resiliente y extensible. 22 agentes, 6 topologías de enjambre, memoria de 3 niveles y auto-reparación.'
            : 'Observable, resilient, and extensible AI workflow execution. 22 agents, 6 swarm topologies, 3-tier memory, and self-healing reliability.'}
        </p>
      </div>

      {/* Step Cards */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
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
