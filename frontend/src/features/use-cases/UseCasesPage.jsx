import { useState, useEffect } from 'react'

const USE_CASES = [
  {
    key: 'analyze',
    icon: '🔍',
    color: '#8B5CF6',
    bg: 'rgba(139,92,246,0.08)',
    agents: 4,
    name: { en: 'AI Analyze', es: 'IA Analizar' },
    desc: {
      en: 'Upload documents or connect Google Drive — AI extracts entities, summarizes, answers questions, and sends results via email.',
      es: 'Sube documentos o conecta Google Drive — la IA extrae entidades, resume, responde preguntas y envía resultados por email.',
    },
    tags: { en: ['RAG', 'Upload', 'Drive', 'Email'], es: ['RAG', 'Subida', 'Drive', 'Email'] },
  },
  {
    key: 'enterprise-ops',
    icon: '🏢',
    color: '#6366F1',
    bg: 'rgba(99,102,241,0.08)',
    agents: 8,
    name: { en: 'Enterprise Ops', es: 'Ops Empresariales' },
    desc: {
      en: 'Multi-agent pipeline: intake, classify intent, CRM update, email, scheduling, notifications — all orchestrated by a supervisor.',
      es: 'Pipeline multi-agente: recepción, clasificación de intención, actualización CRM, email, agenda, notificaciones — todo orquestado por un supervisor.',
    },
    tags: { en: ['CRM', 'Email', 'Scheduling', 'Supervisor'], es: ['CRM', 'Email', 'Agenda', 'Supervisor'] },
  },
  {
    key: 'documents',
    icon: '📄',
    color: '#2563EB',
    bg: 'rgba(37,99,235,0.08)',
    agents: 3,
    name: { en: 'Document Intelligence', es: 'Inteligencia Documental' },
    desc: {
      en: 'RAG pipeline: upload documents, chunk & embed them, then query with semantic search, extraction, and summarization.',
      es: 'Pipeline RAG: sube documentos, fragmenta e indexa, luego consulta con búsqueda semántica, extracción y resumen.',
    },
    tags: { en: ['RAG', 'Embeddings', 'Summary', 'NER'], es: ['RAG', 'Embeddings', 'Resumen', 'NER'] },
  },
  {
    key: 'playground',
    icon: '⚡',
    color: '#F59E0B',
    bg: 'rgba(245,158,11,0.08)',
    agents: 0,
    name: { en: 'Playground', es: 'Playground' },
    desc: {
      en: 'Sandbox to test any agent or chain freely. Send custom prompts, adjust parameters, and see real-time results.',
      es: 'Sandbox para probar cualquier agente o cadena libremente. Envía prompts personalizados, ajusta parámetros y ve resultados en tiempo real.',
    },
    tags: { en: ['Sandbox', 'Custom', 'Testing'], es: ['Sandbox', 'Personalizado', 'Pruebas'] },
  },
]

export default function UseCasesPage({ lang = 'en', onOpenCase }) {
  const [isMobile, setIsMobile] = useState(false)
  const [hoveredKey, setHoveredKey] = useState(null)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          {lang === 'es' ? 'Casos de Uso' : 'Use Cases'}
        </h1>
        <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
          {lang === 'es'
            ? 'Workflows en producción listos para ejecutar. En el futuro, tus workflows personalizados también aparecerán aquí.'
            : 'Production-ready workflows ready to execute. In the future, your custom workflows will also appear here.'}
        </p>
      </div>

      {/* Pre-built use cases */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(340px, 1fr))',
        gap: 20,
        marginBottom: 32,
      }}>
        {USE_CASES.map(uc => (
          <div
            key={uc.key}
            onClick={() => onOpenCase(uc.key)}
            onMouseEnter={() => setHoveredKey(uc.key)}
            onMouseLeave={() => setHoveredKey(null)}
            style={{
              background: '#fff',
              borderRadius: 16,
              border: `1px solid ${hoveredKey === uc.key ? uc.color : '#E5E7EB'}`,
              padding: 24,
              cursor: 'pointer',
              transition: 'all 0.2s',
              boxShadow: hoveredKey === uc.key ? `0 8px 24px ${uc.bg}` : 'none',
            }}
          >
            {/* Icon + badge */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <div style={{
                width: 52, height: 52, borderRadius: 14, background: uc.bg,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 26,
              }}>
                {uc.icon}
              </div>
              <div style={{
                padding: '4px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                background: 'rgba(16,185,129,0.1)', color: '#10B981',
              }}>
                {lang === 'es' ? 'En vivo' : 'Live'}
              </div>
            </div>

            {/* Name */}
            <h3 style={{ fontSize: 17, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
              {uc.name[lang]}
            </h3>

            {/* Description */}
            <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.5, marginBottom: 16, minHeight: 40 }}>
              {uc.desc[lang]}
            </p>

            {/* Tags */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
              {uc.tags[lang].map(tag => (
                <span key={tag} style={{
                  padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 500,
                  background: uc.bg, color: uc.color,
                }}>
                  {tag}
                </span>
              ))}
            </div>

            {/* Footer */}
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              paddingTop: 12, borderTop: '1px solid #F3F4F6',
            }}>
              <span style={{ fontSize: 12, color: '#9CA3AF' }}>
                {uc.agents > 0
                  ? `${uc.agents} ${lang === 'es' ? 'agentes' : 'agents'}`
                  : (lang === 'es' ? 'Personalizable' : 'Customizable')}
              </span>
              <span style={{
                fontSize: 13, fontWeight: 600, color: uc.color,
                display: 'flex', alignItems: 'center', gap: 4,
              }}>
                {lang === 'es' ? 'Ejecutar' : 'Run'}
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M5 12h14m-7-7l7 7-7 7" />
                </svg>
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Future custom workflows placeholder */}
      <div style={{
        padding: 24, borderRadius: 14,
        border: '2px dashed #E5E7EB', textAlign: 'center',
      }}>
        <span style={{ fontSize: 32, display: 'block', marginBottom: 8 }}>+</span>
        <p style={{ fontSize: 14, fontWeight: 600, color: '#6B7280' }}>
          {lang === 'es'
            ? 'Tus workflows personalizados aparecerán aquí'
            : 'Your custom workflows will appear here'}
        </p>
        <p style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4 }}>
          {lang === 'es'
            ? 'Crea un workflow en el Builder y publícalo para verlo en esta sección.'
            : 'Create a workflow in the Builder and publish it to see it in this section.'}
        </p>
      </div>
    </div>
  )
}
