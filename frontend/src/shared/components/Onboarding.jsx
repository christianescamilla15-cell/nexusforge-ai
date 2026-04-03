import { useState } from 'react'

const STEPS = {
  es: [
    {
      icon: '⚡',
      title: 'NexusForge AI',
      description: 'Plataforma SaaS de orquestación IA con 24 agentes, auth + billing Stripe (Free/Pro/Team/Enterprise), AI Workflow Wizard, drag-and-drop builder, 10 integraciones y 4 proveedores LLM (Groq, Claude, GPT-4o, GPT-4o-mini). 260 tests automatizados.',
    },
    {
      icon: '🔐',
      title: 'Autenticación y Billing',
      description: 'Registro por email o Google. Planes: Free (5 ejecuciones/día), Pro $29/mes (100/día), Team $99/mes (500/día), Enterprise (ilimitado). Stripe Checkout integrado, API keys para acceso programático, y modo trial de 10 ejecuciones sin registro.',
    },
    {
      icon: '🧙',
      title: 'Asistente IA de Workflows',
      description: 'Describe lo que quieres automatizar en lenguaje natural y la IA genera el flujo óptimo. 5 pasos: descripción → preguntas → generación → vista previa (editable) → lanzamiento. Guarda como borrador, edita en el Builder, o ejecuta en modo demo.',
    },
    {
      icon: '🔧',
      title: 'Constructor Visual de Flujos',
      description: 'Arrastra agentes al lienzo, conecta puertos de entrada/salida con curvas bezier. 24 agentes con tooltips descriptivos, panel de detalle por nodo, guardar/sobreescribir/crear nuevo. Edita flujos existentes desde la lista de workflows.',
    },
    {
      icon: '🔌',
      title: '10 Integraciones',
      description: 'Entradas: Gmail, Google Drive, Webhook. Salidas: Email (Resend), Notion, Slack, WhatsApp, Webhook, Google Calendar. Cada usuario configura sus propias keys desde el panel de Integraciones. Los flujos se conectan a servicios reales.',
    },
    {
      icon: '🤖',
      title: '4 Proveedores LLM',
      description: 'Groq (Llama 3.3 70B — rápido, $0.59/M tokens), Claude (Sonnet — alta calidad, $3/M), GPT-4o ($2.50/M), GPT-4o-mini ($0.15/M). Cada usuario trae sus propias keys. Circuit breaker con failover automático entre proveedores.',
    },
    {
      icon: 'DAG',
      title: 'Motor de Ejecución DAG',
      description: 'Grafos Acíclicos Dirigidos con algoritmo de Kahn. 6 topologías de enjambre: secuencial, paralelo, jerárquico, debate, consenso y adaptivo. Retry con backoff exponencial, checkpoint/resume, y auto-reparación con 5 estrategias.',
    },
    {
      icon: '🧠',
      title: 'Memoria de 3 Niveles',
      description: 'Trabajo (en proceso, sub-milisegundo), Episódica (Redis, TTL 30 días), Semántica (pgvector, permanente). Los agentes recuerdan entre ejecuciones y comparten conocimiento para decisiones más inteligentes.',
    },
    {
      icon: '📊',
      title: 'Observabilidad y Costos',
      description: 'Dashboard en tiempo real con ejecuciones, tokens, costos. Timeline paso a paso tipo LangSmith. Email automático a Gmail tras cada ejecución con resumen de tokens y costos. Audit trail completo por usuario.',
    },
    {
      icon: '🎯',
      title: 'Agentes Personalizados',
      description: 'Crea tus propios agentes con prompts personalizados (máximo 10 por cuenta). Elige modelo, proveedor, temperatura y tokens. Los agentes custom se ejecutan con tus propias keys y aparecen en el Builder.',
    },
    {
      icon: '📋',
      title: '3 Casos de Uso Reales',
      description: 'Operaciones Empresariales (8 agentes: intake, clasificación, CRM, calendario, notificaciones), Inteligencia Documental (7 agentes: clasificar, extraer, validar, resumir) y Copiloto de Portafolio (6 agentes: RAG, comparación, skills mapping).',
    },
    {
      icon: '🚀',
      title: 'Cómo Empezar',
      description: 'Regístrate o prueba sin cuenta (10 ejecuciones gratis). Usa el AI Wizard para generar tu primer flujo. Configura tus integraciones (Email, Notion, Slack). Ejecuta en modo demo para probar, luego conecta tus keys reales. El dashboard muestra todo en tiempo real.',
    },
  ],
  en: [
    {
      icon: '⚡',
      title: 'NexusForge AI',
      description: 'AI SaaS orchestration platform with 24 agents, auth + Stripe billing (Free/Pro/Team/Enterprise), AI Workflow Wizard, drag-and-drop builder, 10 integrations, and 4 LLM providers (Groq, Claude, GPT-4o, GPT-4o-mini). 260 automated tests.',
    },
    {
      icon: '🔐',
      title: 'Authentication & Billing',
      description: 'Register with email or Google. Plans: Free (5 runs/day), Pro $29/mo (100/day), Team $99/mo (500/day), Enterprise (unlimited). Stripe Checkout integrated, API keys for programmatic access, and trial mode with 10 runs without registration.',
    },
    {
      icon: '🧙',
      title: 'AI Workflow Wizard',
      description: 'Describe what you want to automate in plain language and the AI generates the optimal workflow. 5 steps: describe → clarify → generate → preview (editable) → launch. Save as draft, edit in the Builder, or execute in demo mode.',
    },
    {
      icon: '🔧',
      title: 'Visual Workflow Builder',
      description: 'Drag agents to canvas, connect input/output ports with bezier curves. 24 agents with descriptive tooltips, detail panel per node, save/overwrite/create new. Edit existing workflows from the workflow list.',
    },
    {
      icon: '🔌',
      title: '10 Integrations',
      description: 'Inputs: Gmail, Google Drive, Webhook. Outputs: Email (Resend), Notion, Slack, WhatsApp, Webhook, Google Calendar. Each user configures their own keys from the Integrations panel. Workflows connect to real services.',
    },
    {
      icon: '🤖',
      title: '4 LLM Providers',
      description: 'Groq (Llama 3.3 70B — fast, $0.59/M tokens), Claude (Sonnet — high quality, $3/M), GPT-4o ($2.50/M), GPT-4o-mini ($0.15/M). Each user brings their own keys. Circuit breaker with automatic failover between providers.',
    },
    {
      icon: 'DAG',
      title: 'DAG Execution Engine',
      description: 'Directed Acyclic Graphs with Kahn\'s algorithm. 6 swarm topologies: sequential, parallel, hierarchical, debate, consensus, and adaptive. Retry with exponential backoff, checkpoint/resume, and self-healing with 5 strategies.',
    },
    {
      icon: '🧠',
      title: '3-Tier Memory',
      description: 'Working (in-process, sub-millisecond), Episodic (Redis, 30-day TTL), Semantic (pgvector, permanent). Agents remember across executions and share knowledge for smarter decisions over time.',
    },
    {
      icon: '📊',
      title: 'Observability & Costs',
      description: 'Real-time dashboard with executions, tokens, costs. LangSmith-style step-by-step timeline. Automatic email to Gmail after each execution with token and cost summary. Complete audit trail per user.',
    },
    {
      icon: '🎯',
      title: 'Custom Agents',
      description: 'Create your own agents with custom prompts (max 10 per account). Choose model, provider, temperature, and tokens. Custom agents run with your own keys and appear in the Builder.',
    },
    {
      icon: '📋',
      title: '3 Real Use Cases',
      description: 'Enterprise Operations (8 agents: intake, classification, CRM, calendar, notifications), Document Intelligence (7 agents: classify, extract, validate, summarize), and Portfolio Copilot (6 agents: RAG, comparison, skills mapping).',
    },
    {
      icon: '🚀',
      title: 'Getting Started',
      description: 'Register or try without an account (10 free runs). Use the AI Wizard to generate your first workflow. Configure integrations (Email, Notion, Slack). Execute in demo mode to test, then connect your real keys. The dashboard shows everything in real-time.',
    },
  ],
}

export default function Onboarding({ lang = 'es', setLang, onDismiss }) {
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
      {/* Language selector at the top of onboarding */}
      <div style={{
        display: 'flex', justifyContent: 'center', gap: 8, marginBottom: 16,
      }}>
        {[
          { key: 'es', label: 'Español' },
          { key: 'en', label: 'English' },
        ].map(option => (
          <button
            key={option.key}
            onClick={() => setLang && setLang(option.key)}
            style={{
              padding: '8px 20px', borderRadius: 100, fontSize: 14, fontWeight: 600,
              border: '1px solid',
              borderColor: currentLang === option.key ? '#2563EB' : '#E5E7EB',
              background: currentLang === option.key ? '#2563EB' : '#FFFFFF',
              color: currentLang === option.key ? '#FFFFFF' : '#6B7280',
              cursor: 'pointer', transition: 'all 0.2s ease',
            }}
          >{option.label}</button>
        ))}
      </div>

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
            ? 'Plataforma SaaS de Orquestación IA'
            : 'AI SaaS Orchestration Platform'}
        </h1>
        <p style={{
          fontSize: 16, color: '#4B5563', maxWidth: 640,
          margin: '0 auto', lineHeight: 1.6,
        }}>
          {currentLang === 'es'
            ? '24 agentes IA, auth + billing Stripe, AI Wizard, 10 integraciones, 4 proveedores LLM. Crea flujos de trabajo con IA, configura tus integraciones, y ejecuta en producción.'
            : '24 AI agents, auth + Stripe billing, AI Wizard, 10 integrations, 4 LLM providers. Create workflows with AI, configure your integrations, and execute in production.'}
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
