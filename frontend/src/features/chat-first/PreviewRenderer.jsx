/**
 * Renders different preview types based on the current state of the conversation.
 * Shows visual feedback of what's being built in real-time.
 */

const STEP_CONFIG = {
  source: { icon: '\uD83D\uDCE5', color: '#2563EB', labelEs: 'Configurando entrada de datos', labelEn: 'Configuring data input' },
  processing: { icon: '\u2699\uFE0F', color: '#7C3AED', labelEs: 'Definiendo procesamiento', labelEn: 'Defining processing' },
  output: { icon: '\uD83D\uDCE4', color: '#059669', labelEs: 'Configurando salidas', labelEn: 'Configuring outputs' },
  customize: { icon: '\uD83C\uDFA8', color: '#D97706', labelEs: 'Personalizando', labelEn: 'Customizing' },
}

function StepIndicator({ step, lang }) {
  const config = STEP_CONFIG[step] || STEP_CONFIG.source
  const steps = ['source', 'processing', 'output', 'customize']
  const currentIdx = steps.indexOf(step)

  return (
    <div style={{ padding: 20 }}>
      {/* Progress bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {steps.map((s, i) => {
          const sc = STEP_CONFIG[s]
          const isActive = i === currentIdx
          const isDone = i < currentIdx
          return (
            <div key={s} style={{ flex: 1, textAlign: 'center' }}>
              <div style={{
                height: 4, borderRadius: 2, marginBottom: 8,
                background: isDone ? '#059669' : isActive ? sc.color : '#E5E7EB',
                transition: 'background 0.5s',
              }} />
              <div style={{
                fontSize: 20, marginBottom: 4,
                opacity: isActive ? 1 : isDone ? 0.5 : 0.3,
                transition: 'opacity 0.3s',
              }}>
                {isDone ? '\u2705' : sc.icon}
              </div>
              <div style={{
                fontSize: 10, color: isActive ? sc.color : '#9CA3AF',
                fontWeight: isActive ? 700 : 400,
              }}>
                {lang === 'es' ? sc.labelEs : sc.labelEn}
              </div>
            </div>
          )
        })}
      </div>

      {/* Current step highlight */}
      <div style={{
        padding: 20, borderRadius: 16,
        background: `linear-gradient(135deg, ${config.color}08, ${config.color}15)`,
        border: `2px solid ${config.color}30`,
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>{config.icon}</div>
        <div style={{ fontSize: 15, fontWeight: 700, color: config.color }}>
          {lang === 'es' ? config.labelEs : config.labelEn}
        </div>
      </div>
    </div>
  )
}

function BuildingAnimation({ lang }) {
  return (
    <div style={{ padding: 20, textAlign: 'center' }}>
      <div style={{
        width: 80, height: 80, margin: '0 auto 20px',
        borderRadius: '50%',
        background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        animation: 'pulse 2s infinite',
      }}>
        <span style={{ fontSize: 36, color: '#fff' }}>{'\u2692\uFE0F'}</span>
      </div>
      <div style={{ fontSize: 16, fontWeight: 700, color: '#6366F1', marginBottom: 8 }}>
        {lang === 'es' ? 'Construyendo tu automatizaci\u00F3n...' : 'Building your automation...'}
      </div>
      <div style={{ fontSize: 13, color: '#9CA3AF' }}>
        {lang === 'es' ? 'Configurando agentes, reglas y conexiones' : 'Setting up agents, rules, and connections'}
      </div>

      {/* Animated blocks */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 24 }}>
        {['\uD83D\uDCE5', '\uD83E\uDD16', '\uD83D\uDCE4'].map((icon, i) => (
          <div key={i} style={{
            width: 50, height: 50, borderRadius: 12,
            background: '#EEF2FF', border: '1px solid #C7D2FE',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22,
            animation: `pulse 1.5s ease-in-out ${i * 0.3}s infinite`,
          }}>
            {icon}
          </div>
        ))}
      </div>
    </div>
  )
}

function CompleteSummary({ data, lang }) {
  return (
    <div style={{ padding: 20 }}>
      <div style={{
        padding: 24, borderRadius: 16,
        background: 'linear-gradient(135deg, #F0FDF4, #DCFCE7)',
        border: '2px solid #86EFAC',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>{'\u2705'}</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: '#166534', marginBottom: 8 }}>
          {lang === 'es' ? '\u00A1Automatizaci\u00F3n lista!' : 'Automation ready!'}
        </div>
        {data?.name && (
          <div style={{
            display: 'inline-block', padding: '6px 16px', borderRadius: 20,
            background: '#fff', border: '1px solid #86EFAC',
            fontSize: 14, fontWeight: 600, color: '#059669',
            marginBottom: 12,
          }}>
            {data.name}
          </div>
        )}
        {data?.text && (
          <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.6, marginTop: 12 }}>
            {data.text}
          </div>
        )}
      </div>
    </div>
  )
}

function IdlePreview({ lang }) {
  return (
    <div style={{ padding: 20, textAlign: 'center' }}>
      <div style={{
        fontSize: 48, marginBottom: 16, opacity: 0.5,
      }}>
        {'\uD83D\uDE80'}
      </div>
      <div style={{ fontSize: 16, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
        {lang === 'es' ? 'Vista previa en vivo' : 'Live preview'}
      </div>
      <div style={{ fontSize: 13, color: '#9CA3AF', lineHeight: 1.6, maxWidth: 280, margin: '0 auto' }}>
        {lang === 'es'
          ? 'Empieza a describir tu automatizaci\u00F3n en el chat y ver\u00E1s c\u00F3mo se construye aqu\u00ED en tiempo real.'
          : 'Start describing your automation in the chat and watch it build here in real-time.'}
      </div>

      {/* Mini feature cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 24 }}>
        {[
          { icon: '\uD83C\uDFAB', labelEs: 'Tickets', labelEn: 'Tickets' },
          { icon: '\uD83D\uDCC4', labelEs: 'Documentos', labelEn: 'Documents' },
          { icon: '\uD83D\uDCE7', labelEs: 'Emails', labelEn: 'Emails' },
          { icon: '\uD83D\uDCCA', labelEs: 'Reportes', labelEn: 'Reports' },
        ].map(item => (
          <div key={item.icon} style={{
            padding: '14px 10px', borderRadius: 12,
            background: '#F9FAFB', border: '1px solid #E5E7EB',
          }}>
            <div style={{ fontSize: 24, marginBottom: 4 }}>{item.icon}</div>
            <div style={{ fontSize: 11, color: '#6B7280' }}>
              {lang === 'es' ? item.labelEs : item.labelEn}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function PreviewRenderer({ previewState, lang = 'es' }) {
  const { type, data } = previewState

  switch (type) {
    case 'step':
      return <StepIndicator step={data?.step || 'source'} lang={lang} />
    case 'building':
      return <BuildingAnimation lang={lang} />
    case 'complete':
      return <CompleteSummary data={data} lang={lang} />
    default:
      return <IdlePreview lang={lang} />
  }
}
