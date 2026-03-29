import { useState } from 'react'

const STEPS = [
  {
    icon: '{ }',
    title: 'NexusForge AI: Enterprise Multi-Agent Orchestration Platform',
    description: 'A production-grade platform for orchestrating autonomous AI agents at scale. Build, deploy, and monitor intelligent workflows with full observability and enterprise reliability.',
  },
  {
    icon: 'DAG',
    title: 'Workflow Execution: DAG + Swarm',
    description: 'Define workflows as Directed Acyclic Graphs (DAGs) that chain specialized agents. Choose from 6 swarm topologies -- sequential, parallel, hierarchical, debate, consensus, and adaptive -- to match your use case.',
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
    icon: 'GO',
    title: 'Getting Started',
    description: 'Explore the Dashboard for system health at a glance. Use Workflows to build pipelines. Monitor Executions in real-time. The AI Assistant is always available to answer questions.',
  },
]

export default function Onboarding({ lang, onDismiss }) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  const handleDismiss = () => {
    setDismissed(true)
    if (onDismiss) onDismiss()
  }

  return (
    <div style={{
      padding: '0 0 32px',
      animation: 'fadeIn 0.4s ease-out',
    }}>
      {/* Hero Section */}
      <div style={{
        textAlign: 'center',
        padding: '48px 24px 40px',
        marginBottom: 32,
        background: '#FFFFFF',
        borderRadius: 16,
        border: '1px solid #E5E7EB',
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
          Enterprise Multi-Agent Orchestration Platform
        </h1>
        <p style={{
          fontSize: 16, color: '#4B5563', maxWidth: 560,
          margin: '0 auto', lineHeight: 1.6,
        }}>
          Observable, resilient, and extensible AI workflow execution.
          {' '}22 agents, 6 swarm topologies, 3-tier memory, and self-healing reliability.
        </p>
      </div>

      {/* Step Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: 16,
        marginBottom: 24,
      }}>
        {STEPS.map((step, i) => (
          <div key={i} style={{
            background: '#FFFFFF',
            border: '1px solid #E5E7EB',
            borderRadius: 12,
            padding: '24px 24px 20px',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            transition: 'box-shadow 0.2s, border-color 0.2s',
          }}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.06)'
              e.currentTarget.style.borderColor = 'rgba(37,99,235,0.3)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = '0 1px 2px rgba(0,0,0,0.04)'
              e.currentTarget.style.borderColor = '#E5E7EB'
            }}
          >
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12,
            }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: 'rgba(37,99,235,0.06)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#2563EB', fontWeight: 700, fontSize: 12,
                fontFamily: 'monospace',
                border: '1px solid rgba(37,99,235,0.12)',
                flexShrink: 0,
              }}>
                {step.icon}
              </div>
              <div style={{
                fontSize: 11, fontWeight: 600, color: '#9CA3AF',
                textTransform: 'uppercase', letterSpacing: '0.06em',
              }}>
                Step {i + 1} of {STEPS.length}
              </div>
            </div>
            <h3 style={{
              fontSize: 15, fontWeight: 600, color: '#111827',
              marginBottom: 8, lineHeight: 1.4,
            }}>
              {step.title}
            </h3>
            <p style={{
              fontSize: 14, color: '#4B5563', lineHeight: 1.6,
            }}>
              {step.description}
            </p>
          </div>
        ))}
      </div>

      {/* Dismiss Button */}
      <div style={{ textAlign: 'center' }}>
        <button
          onClick={handleDismiss}
          style={{
            padding: '10px 28px', borderRadius: 8, border: 'none',
            background: '#2563EB', color: '#FFFFFF',
            fontSize: 14, fontWeight: 600, cursor: 'pointer',
            transition: 'background 0.15s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = '#1D4ED8'}
          onMouseLeave={(e) => e.currentTarget.style.background = '#2563EB'}
        >
          {lang === 'es' ? 'Ir al Dashboard' : 'Go to Dashboard'}
        </button>
      </div>
    </div>
  )
}
