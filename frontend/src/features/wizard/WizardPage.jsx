import { useState, useCallback, useRef, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

// ── Translations ─────────────────────────────────────────────────────────────

const T = {
  steps: {
    es: ['Describir', 'Entrada', 'Salida', 'Vista previa', 'Publicar'],
    en: ['Describe', 'Input', 'Output', 'Preview', 'Publish'],
  },
  title: { es: 'Asistente de Automatizaciones IA', en: 'AI Automation Wizard' },
  subtitle: {
    es: 'Describe lo que quieres automatizar — la IA diseña el flujo, el dashboard y todo lo necesario.',
    en: 'Describe what you want to automate — the AI designs the workflow, dashboard and everything you need.',
  },
  // Step 0
  step0Title: { es: '¿Qué quieres automatizar?', en: 'What do you want to automate?' },
  step0Desc: {
    es: 'Elige un tipo o describe tu automatización. La IA diseñará el pipeline óptimo.',
    en: 'Pick a type or describe your automation. The AI will design the optimal pipeline.',
  },
  step0Placeholder: {
    es: 'Ej: Leer correos de Gmail, clasificar por urgencia, resumir cada uno y enviar resumen a Slack...',
    en: 'e.g. Read emails from Gmail, classify them by urgency, summarize each one, and send digest to Slack...',
  },
  // Step 1 (Input)
  step1Title: { es: '¿Cómo entrarán los datos?', en: 'How will data enter your automation?' },
  step1Desc: {
    es: 'Selecciona cómo se alimentará tu automatización.',
    en: 'Select how your automation will be fed.',
  },
  // Step 2 (Output)
  step2Title: { es: '¿Qué hacer con los resultados?', en: 'What should happen with the results?' },
  step2Desc: {
    es: 'Elige uno o más destinos para los resultados de tu automatización.',
    en: 'Pick one or more destinations for your automation results.',
  },
  // Step 3 (Preview)
  step3Title: { es: 'Vista previa de tu automatización', en: 'Preview your automation' },
  step3Desc: {
    es: 'Revisa el pipeline, entradas, salidas y dashboard antes de publicar.',
    en: 'Review the pipeline, inputs, outputs and dashboard before publishing.',
  },
  // Step 4 (Publish)
  step4Title: { es: '¡Publicar automatización!', en: 'Publish your automation!' },
  step4Desc: {
    es: 'Se creará el workflow, la automatización y su dashboard. Estarás listo para ejecutar.',
    en: 'The workflow, automation and dashboard will be created. You\'ll be ready to run.',
  },
  // Common
  next: { es: 'Siguiente', en: 'Next' },
  back: { es: 'Atrás', en: 'Back' },
  generating: { es: 'Generando tu automatización...', en: 'Generating your automation...' },
  generatingDesc: {
    es: 'La IA está seleccionando los mejores agentes y diseñando las dependencias...',
    en: 'The AI is selecting the best agents and designing dependencies...',
  },
  publish: { es: 'Publicar Automatización', en: 'Publish Automation' },
  publishing: { es: 'Publicando...', en: 'Publishing...' },
  characters: { es: 'caracteres', en: 'characters' },
  pipeline: { es: 'Pipeline', en: 'Pipeline' },
  stepsLabel: { es: 'pasos', en: 'steps' },
  inputType: { es: 'Tipo de entrada', en: 'Input type' },
  outputDest: { es: 'Destinos de salida', en: 'Output destinations' },
  dashboardType: { es: 'Tipo de dashboard', en: 'Dashboard type' },
  dashboardPreview: { es: 'Vista previa del Dashboard', en: 'Dashboard Preview' },
  editName: { es: 'Nombre del flujo', en: 'Workflow name' },
  namePlaceholder: { es: 'Ej: Proceso de Facturas', en: 'Ex: Invoice Processing' },
  descLabel: { es: 'Descripción del flujo', en: 'Workflow description' },
  quickSelect: { es: 'Selecciona un tipo:', en: 'Select a type:' },
  orDescribe: { es: 'O describe tu automatización personalizada:', en: 'Or describe your custom automation:' },
  generateFlow: { es: 'Generar Flujo', en: 'Generate Workflow' },
}

const t = (key, lang) => (T[key] && T[key][lang]) || (T[key] && T[key].en) || key

// ── Quick-select types ───────────────────────────────────────────────────────

const QUICK_TYPES = [
  {
    key: 'ticket', icon: '\uD83C\uDFAB',
    label: { es: 'Triage de Tickets', en: 'Ticket Triage' },
    description: {
      es: 'Clasificar tickets de soporte por urgencia y generar respuestas',
      en: 'Classify support tickets by urgency and generate responses',
    },
  },
  {
    key: 'document', icon: '\uD83D\uDCC4',
    label: { es: 'Análisis de Documentos', en: 'Document Analysis' },
    description: {
      es: 'Extraer datos de PDFs, facturas y documentos',
      en: 'Extract data from PDFs, invoices and documents',
    },
  },
  {
    key: 'email', icon: '\uD83D\uDCE7',
    label: { es: 'Auto-Respuesta Email', en: 'Email Auto-Responder' },
    description: {
      es: 'Clasificar emails y generar respuestas automáticas',
      en: 'Classify emails and generate automatic responses',
    },
  },
  {
    key: 'report', icon: '\uD83D\uDCCA',
    label: { es: 'Generador de Reportes', en: 'Report Generator' },
    description: {
      es: 'Analizar datos y generar reportes ejecutivos',
      en: 'Analyze data and generate executive reports',
    },
  },
  {
    key: 'custom', icon: '\u26A1',
    label: { es: 'Personalizado', en: 'Custom' },
    description: {
      es: 'Describe tu automatización y la IA la construirá',
      en: 'Describe your automation and AI will build it',
    },
  },
]

// ── Quick-type smart defaults ────────────────────────────────────────────────

const QUICK_TYPE_DEFAULTS = {
  ticket:   { input: 'text',   outputs: ['dashboard', 'slack'] },
  document: { input: 'file',   outputs: ['dashboard', 'export'] },
  email:    { input: 'text',   outputs: ['dashboard', 'email'] },
  report:   { input: 'form',   outputs: ['dashboard', 'export'] },
  custom:   { input: null,     outputs: [] },
}

// ── Input options ────────────────────────────────────────────────────────────

const INPUT_OPTIONS = [
  { key: 'text', icon: '\uD83D\uDCDD', label: { es: 'Texto', en: 'Text input' }, desc: { es: 'Pegar texto directamente', en: 'Paste text directly' } },
  { key: 'file', icon: '\uD83D\uDCC4', label: { es: 'Archivo', en: 'File upload' }, desc: { es: 'PDF, DOCX, imágenes', en: 'PDF, DOCX, images' } },
  { key: 'form', icon: '\uD83D\uDCCB', label: { es: 'Formulario', en: 'Form' }, desc: { es: 'Campos personalizados', en: 'Custom fields' } },
  { key: 'webhook', icon: '\uD83D\uDD17', label: { es: 'Webhook', en: 'Webhook' }, desc: { es: 'Trigger externo', en: 'External trigger' } },
  { key: 'email', icon: '\uD83D\uDCE7', label: { es: 'Email', en: 'Email' }, desc: { es: 'Integración Gmail', en: 'Gmail integration' } },
]

// ── Output options ───────────────────────────────────────────────────────────

const OUTPUT_OPTIONS = [
  { key: 'dashboard', icon: '\uD83D\uDCCA', label: { es: 'Dashboard', en: 'Dashboard' }, desc: { es: 'Ver en NexusForge', en: 'View in NexusForge' } },
  { key: 'email', icon: '\uD83D\uDCE7', label: { es: 'Email', en: 'Email notification' }, desc: { es: 'Notificación por email', en: 'Send email notification' } },
  { key: 'slack', icon: '\uD83D\uDCAC', label: { es: 'Slack', en: 'Slack notification' }, desc: { es: 'Notificación a Slack', en: 'Send to Slack' } },
  { key: 'notion', icon: '\uD83D\uDCDD', label: { es: 'Notion', en: 'Save to Notion' }, desc: { es: 'Guardar en Notion', en: 'Save to Notion database' } },
  { key: 'export', icon: '\uD83D\uDCE5', label: { es: 'Exportar CSV/PDF', en: 'Export CSV/PDF' }, desc: { es: 'Descargar resultados', en: 'Download results' } },
  { key: 'webhook', icon: '\uD83D\uDD17', label: { es: 'Webhook', en: 'Webhook' }, desc: { es: 'Enviar a sistema externo', en: 'Send to external system' } },
]

// ── Agent colors ─────────────────────────────────────────────────────────────

const AGENT_COLORS = {
  classifier: '#2563EB', extractor: '#059669', summarizer: '#7C3AED',
  analyzer: '#D97706', enricher: '#0891B2', validator: '#DC2626',
  reporter: '#DB2777', repair: '#6366F1', normalizer: '#0D9488',
  researcher: '#B45309', translator: '#4F46E5', compliance: '#BE185D',
  monitor: '#0369A1', planner: '#9333EA', knowledge: '#1D4ED8',
  scraper: '#B91C1C', ocr: '#0F766E', sentiment: '#C2410C',
  scheduler: '#6D28D9', webhook: '#374151',
}
const agentColor = (type) => AGENT_COLORS[type] || '#6B7280'

// ── Dashboard type mapping ───────────────────────────────────────────────────

const DASHBOARD_TYPE_MAP = {
  ticket: 'ticket',
  document: 'document',
  email: 'email',
  report: 'report',
  custom: 'generic',
}

const DASHBOARD_TYPE_LABELS = {
  ticket: { es: 'Ticket Dashboard', en: 'Ticket Dashboard' },
  document: { es: 'Document Dashboard', en: 'Document Dashboard' },
  email: { es: 'Email Dashboard', en: 'Email Dashboard' },
  report: { es: 'Report Dashboard', en: 'Report Dashboard' },
  generic: { es: 'Dashboard Genérico', en: 'Generic Dashboard' },
}

// ── Icon map for automation types ────────────────────────────────────────────

const TYPE_ICON_MAP = {
  ticket: '\uD83C\uDFAB',
  document: '\uD83D\uDCC4',
  email: '\uD83D\uDCE7',
  report: '\uD83D\uDCCA',
  custom: '\u26A1',
}

const TYPE_COLOR_MAP = {
  ticket: '#2563EB',
  document: '#059669',
  email: '#D97706',
  report: '#7C3AED',
  custom: '#6366F1',
}

// ── Progress bar ─────────────────────────────────────────────────────────────

function ProgressBar({ step, lang = 'en' }) {
  const STEPS = T.steps[lang] || T.steps.en
  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        {STEPS.map((label, i) => (
          <div key={label} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%', display: 'flex',
              alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700,
              background: i < step ? '#6366F1' : i === step ? '#818CF8' : '#E5E7EB',
              color: i <= step ? '#fff' : '#9CA3AF',
              border: i === step ? '2px solid #6366F1' : 'none',
              transition: 'all 0.3s',
            }}>
              {i < step ? '\u2713' : i + 1}
            </div>
            <span style={{ fontSize: 10, color: i <= step ? '#6366F1' : '#9CA3AF', marginTop: 4, fontWeight: i === step ? 700 : 400 }}>
              {label}
            </span>
          </div>
        ))}
      </div>
      <div style={{ height: 3, background: '#E5E7EB', borderRadius: 2, position: 'relative' }}>
        <div style={{
          height: '100%', borderRadius: 2, background: 'linear-gradient(90deg, #6366F1, #818CF8)',
          width: `${(step / (STEPS.length - 1)) * 100}%`, transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  )
}

// ── Step 0: Describe ─────────────────────────────────────────────────────────

function StepDescribe({ description, onChange, workflowName, onNameChange, selectedType, onTypeChange, lang = 'en' }) {
  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        {t('step0Title', lang)}
      </h2>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 24 }}>
        {t('step0Desc', lang)}
      </p>

      {/* Quick-select chips */}
      <p style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 12 }}>
        {t('quickSelect', lang)}
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10, marginBottom: 24 }}>
        {QUICK_TYPES.map((qt) => {
          const isSelected = selectedType === qt.key
          return (
            <button
              key={qt.key}
              onClick={() => {
                onTypeChange(qt.key)
                if (qt.key !== 'custom') {
                  onChange(qt.description[lang])
                  if (!workflowName.trim()) onNameChange(qt.label[lang])
                }
              }}
              style={{
                padding: '14px 16px', borderRadius: 12, border: '2px solid',
                borderColor: isSelected ? '#6366F1' : '#E5E7EB',
                background: isSelected ? '#EEF2FF' : '#fff',
                cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s',
              }}
            >
              <div style={{ fontSize: 24, marginBottom: 6 }}>{qt.icon}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: isSelected ? '#6366F1' : '#111827', marginBottom: 2 }}>
                {qt.label[lang]}
              </div>
              <div style={{ fontSize: 11, color: '#9CA3AF', lineHeight: 1.4 }}>
                {qt.description[lang]}
              </div>
            </button>
          )
        })}
      </div>

      {/* Name field */}
      <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
        {t('editName', lang)}
      </label>
      <input
        value={workflowName}
        onChange={(e) => onNameChange(e.target.value)}
        placeholder={t('namePlaceholder', lang)}
        style={{
          width: '100%', padding: '10px 14px', borderRadius: 8, fontSize: 14,
          border: '2px solid #E5E7EB', outline: 'none', boxSizing: 'border-box',
          marginBottom: 16, fontFamily: 'inherit', transition: 'border-color 0.15s',
        }}
        onFocus={(e) => e.target.style.borderColor = '#6366F1'}
        onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
      />

      {/* Description */}
      <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
        {selectedType === 'custom' ? t('orDescribe', lang) : t('descLabel', lang)}
      </label>
      <textarea
        value={description}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t('step0Placeholder', lang)}
        rows={4}
        autoFocus={selectedType === 'custom'}
        style={{
          width: '100%', padding: '14px 16px', borderRadius: 10, fontSize: 14,
          border: '2px solid #E5E7EB', outline: 'none', resize: 'vertical',
          lineHeight: 1.6, boxSizing: 'border-box', fontFamily: 'inherit',
          transition: 'border-color 0.15s',
        }}
        onFocus={(e) => e.target.style.borderColor = '#6366F1'}
        onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
      />
      <p style={{ fontSize: 12, color: '#9CA3AF', marginTop: 6 }}>
        {description.length} {t('characters', lang)}
      </p>
    </div>
  )
}

// ── Step 1: Input Configuration ──────────────────────────────────────────────

function StepInput({ selected, onSelect, lang = 'en' }) {
  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        {t('step1Title', lang)}
      </h2>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 24 }}>
        {t('step1Desc', lang)}
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
        {INPUT_OPTIONS.map((opt) => {
          const isSelected = selected === opt.key
          return (
            <button
              key={opt.key}
              onClick={() => onSelect(opt.key)}
              style={{
                padding: '20px 18px', borderRadius: 14, border: '2px solid',
                borderColor: isSelected ? '#6366F1' : '#E5E7EB',
                background: isSelected ? '#EEF2FF' : '#fff',
                cursor: 'pointer', textAlign: 'left', transition: 'all 0.2s',
                display: 'flex', flexDirection: 'column', gap: 6,
              }}
            >
              <div style={{ fontSize: 28 }}>{opt.icon}</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: isSelected ? '#6366F1' : '#111827' }}>
                {opt.label[lang]}
              </div>
              <div style={{ fontSize: 12, color: '#9CA3AF', lineHeight: 1.4 }}>
                {opt.desc[lang]}
              </div>
              {isSelected && (
                <div style={{
                  marginTop: 4, fontSize: 11, fontWeight: 700, color: '#6366F1',
                  display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  <span style={{
                    width: 16, height: 16, borderRadius: '50%', background: '#6366F1',
                    color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 10,
                  }}>{'\u2713'}</span>
                  {lang === 'es' ? 'Seleccionado' : 'Selected'}
                </div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Step 2: Output Configuration ─────────────────────────────────────────────

function StepOutput({ selected, onToggle, lang = 'en' }) {
  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        {t('step2Title', lang)}
      </h2>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 24 }}>
        {t('step2Desc', lang)}
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
        {OUTPUT_OPTIONS.map((opt) => {
          const isSelected = selected.includes(opt.key)
          return (
            <button
              key={opt.key}
              onClick={() => onToggle(opt.key)}
              style={{
                padding: '20px 18px', borderRadius: 14, border: '2px solid',
                borderColor: isSelected ? '#059669' : '#E5E7EB',
                background: isSelected ? '#F0FDF4' : '#fff',
                cursor: 'pointer', textAlign: 'left', transition: 'all 0.2s',
                display: 'flex', flexDirection: 'column', gap: 6,
              }}
            >
              <div style={{ fontSize: 28 }}>{opt.icon}</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: isSelected ? '#059669' : '#111827' }}>
                {opt.label[lang]}
              </div>
              <div style={{ fontSize: 12, color: '#9CA3AF', lineHeight: 1.4 }}>
                {opt.desc[lang]}
              </div>
              {isSelected && (
                <div style={{
                  marginTop: 4, fontSize: 11, fontWeight: 700, color: '#059669',
                  display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  <span style={{
                    width: 16, height: 16, borderRadius: '50%', background: '#059669',
                    color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 10,
                  }}>{'\u2713'}</span>
                  {lang === 'es' ? 'Seleccionado' : 'Selected'}
                </div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Generating spinner (between describe and input) ──────────────────────────

function StepGenerating({ lang = 'en' }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 0' }}>
      <div style={{
        width: 64, height: 64, borderRadius: '50%', margin: '0 auto 24px',
        border: '4px solid #E5E7EB', borderTopColor: '#6366F1',
        animation: 'wizardSpin 0.8s linear infinite',
      }} />
      <style>{`@keyframes wizardSpin { to { transform: rotate(360deg) } }`}</style>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        {t('generating', lang)}
      </h2>
      <p style={{ fontSize: 14, color: '#9CA3AF' }}>
        {t('generatingDesc', lang)}
      </p>
    </div>
  )
}

// ── Dashboard Preview mockup ─────────────────────────────────────────────────

function DashboardPreviewMockup({ type, lang = 'en' }) {
  const mockStyle = {
    padding: '16px 18px', borderRadius: 12, border: '1px dashed #C7D2FE',
    background: '#FAFAFE',
  }
  const barStyle = (w, color) => ({
    height: 8, borderRadius: 4, background: color, width: w, marginBottom: 6,
  })
  const cardStyle = {
    background: '#fff', borderRadius: 8, padding: '10px 12px', border: '1px solid #E5E7EB',
  }

  if (type === 'ticket') {
    return (
      <div style={mockStyle}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          {['#EF4444', '#F59E0B', '#10B981'].map((c, i) => (
            <div key={i} style={{ ...cardStyle, flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: c }}>{[12, 8, 24][i]}</div>
              <div style={{ fontSize: 10, color: '#9CA3AF' }}>
                {lang === 'es' ? ['Urgente', 'Pendiente', 'Resuelto'][i] : ['Urgent', 'Pending', 'Resolved'][i]}
              </div>
            </div>
          ))}
        </div>
        <div style={barStyle('80%', '#6366F1')} />
        <div style={barStyle('55%', '#818CF8')} />
        <div style={barStyle('30%', '#C7D2FE')} />
      </div>
    )
  }

  if (type === 'document') {
    return (
      <div style={mockStyle}>
        <div style={{
          border: '2px dashed #C7D2FE', borderRadius: 10, padding: '16px', textAlign: 'center',
          marginBottom: 12, background: '#EEF2FF',
        }}>
          <div style={{ fontSize: 24, marginBottom: 4 }}>{'\uD83D\uDCC1'}</div>
          <div style={{ fontSize: 11, color: '#6366F1', fontWeight: 600 }}>
            {lang === 'es' ? 'Zona de subida de archivos' : 'File upload zone'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {[1, 2].map(i => (
            <div key={i} style={{ ...cardStyle, flex: 1 }}>
              <div style={barStyle('70%', '#059669')} />
              <div style={barStyle('50%', '#BBF7D0')} />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (type === 'email') {
    return (
      <div style={mockStyle}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          {['#2563EB', '#F59E0B'].map((c, i) => (
            <div key={i} style={{ ...cardStyle, flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: c }}>{[156, 34][i]}</div>
              <div style={{ fontSize: 10, color: '#9CA3AF' }}>
                {lang === 'es' ? ['Procesados', 'Pendientes'][i] : ['Processed', 'Pending'][i]}
              </div>
            </div>
          ))}
        </div>
        {[1, 2, 3].map(i => (
          <div key={i} style={{ ...cardStyle, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: ['#10B981', '#F59E0B', '#EF4444'][i - 1] }} />
            <div style={barStyle(`${70 - i * 15}%`, '#E5E7EB')} />
          </div>
        ))}
      </div>
    )
  }

  if (type === 'report') {
    return (
      <div style={mockStyle}>
        <div style={{ ...cardStyle, marginBottom: 10, textAlign: 'center' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#7C3AED', marginBottom: 6 }}>
            {lang === 'es' ? 'Reporte Ejecutivo' : 'Executive Report'}
          </div>
          <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
            {[40, 65, 50, 80, 45].map((h, i) => (
              <div key={i} style={{ width: 18, height: h * 0.6, background: '#7C3AED', borderRadius: 3, opacity: 0.3 + i * 0.15 }} />
            ))}
          </div>
        </div>
        <div style={barStyle('90%', '#7C3AED')} />
        <div style={barStyle('60%', '#C4B5FD')} />
      </div>
    )
  }

  // generic
  return (
    <div style={mockStyle}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        {[1, 2, 3].map(i => (
          <div key={i} style={{ ...cardStyle, flex: 1, textAlign: 'center' }}>
            <div style={barStyle('60%', '#6366F1')} />
            <div style={{ fontSize: 10, color: '#9CA3AF' }}>KPI {i}</div>
          </div>
        ))}
      </div>
      <div style={barStyle('75%', '#818CF8')} />
      <div style={barStyle('45%', '#C7D2FE')} />
    </div>
  )
}

// ── Step 3: Preview ──────────────────────────────────────────────────────────

function StepPreview({ workflow, inputType, outputTypes, automationType, onUpdateName, onChangeInputOutput, skippedInputOutput, lang = 'en' }) {
  if (!workflow) return null
  const { name, steps = [], recommended_topology, topology_reason, estimated_tokens, estimated_cost_usd } = workflow
  const dashType = DASHBOARD_TYPE_MAP[automationType] || 'generic'
  const dashLabel = DASHBOARD_TYPE_LABELS[dashType]?.[lang] || 'Dashboard'

  const inputLabel = INPUT_OPTIONS.find(o => o.key === inputType)
  const selectedOutputs = OUTPUT_OPTIONS.filter(o => outputTypes.includes(o.key))

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        {t('step3Title', lang)}
      </h2>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 24 }}>
        {t('step3Desc', lang)}
      </p>

      {/* Editable name */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20,
        padding: '12px 16px', borderRadius: 10, background: '#EEF2FF', border: '1px solid #C7D2FE',
      }}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366F1" strokeWidth="2" strokeLinecap="round">
          <path d="M4 6h16M4 12h8m-8 6h16" />
        </svg>
        <input
          value={name}
          onChange={(e) => onUpdateName && onUpdateName(e.target.value)}
          style={{
            fontSize: 15, fontWeight: 700, color: '#4338CA', border: 'none', outline: 'none',
            background: 'transparent', flex: 1, fontFamily: 'inherit',
          }}
          placeholder={lang === 'es' ? 'Nombre del flujo...' : 'Workflow name...'}
        />
        {estimated_tokens && (
          <span style={{ fontSize: 12, color: '#6366F1', flexShrink: 0 }}>
            ~{estimated_tokens} tokens {estimated_cost_usd ? `\u00B7 ~$${(estimated_cost_usd).toFixed(4)}` : ''}
          </span>
        )}
      </div>

      {/* Config summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 20 }}>
        {/* Input */}
        <div style={{
          padding: '12px 14px', borderRadius: 10, background: '#F0F9FF', border: '1px solid #BAE6FD',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#0284C7', textTransform: 'uppercase' }}>
              {t('inputType', lang)}
            </div>
            {skippedInputOutput && onChangeInputOutput && (
              <button onClick={onChangeInputOutput} style={{
                background: 'none', border: 'none', fontSize: 11, fontWeight: 600,
                color: '#0284C7', cursor: 'pointer', textDecoration: 'underline', padding: 0,
              }}>
                {lang === 'es' ? 'Cambiar' : 'Change'}
              </button>
            )}
          </div>
          <div style={{ fontSize: 20, marginBottom: 2 }}>{inputLabel?.icon || '\uD83D\uDCDD'}</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{inputLabel?.label[lang] || inputType}</div>
        </div>
        {/* Outputs */}
        <div style={{
          padding: '12px 14px', borderRadius: 10, background: '#F0FDF4', border: '1px solid #BBF7D0',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#16A34A', textTransform: 'uppercase' }}>
              {t('outputDest', lang)}
            </div>
            {skippedInputOutput && onChangeInputOutput && (
              <button onClick={onChangeInputOutput} style={{
                background: 'none', border: 'none', fontSize: 11, fontWeight: 600,
                color: '#16A34A', cursor: 'pointer', textDecoration: 'underline', padding: 0,
              }}>
                {lang === 'es' ? 'Cambiar' : 'Change'}
              </button>
            )}
          </div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {selectedOutputs.map(o => (
              <span key={o.key} style={{ fontSize: 18 }}>{o.icon}</span>
            ))}
          </div>
          <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>
            {selectedOutputs.map(o => o.label[lang]).join(', ')}
          </div>
        </div>
        {/* Dashboard type */}
        <div style={{
          padding: '12px 14px', borderRadius: 10, background: '#FAF5FF', border: '1px solid #E9D5FF',
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#7C3AED', textTransform: 'uppercase', marginBottom: 6 }}>
            {t('dashboardType', lang)}
          </div>
          <div style={{ fontSize: 20, marginBottom: 2 }}>{TYPE_ICON_MAP[automationType] || '\u26A1'}</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{dashLabel}</div>
        </div>
      </div>

      {/* Pipeline */}
      <div style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 12, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 12 }}>
          {t('pipeline', lang)} ({steps.length} {t('stepsLabel', lang)})
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {steps.map((step, i) => (
            <div key={step.name} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 14px', borderRadius: 8, background: '#fff',
              border: `1px solid ${agentColor(step.agent_type)}30`,
            }}>
              <div style={{
                width: 24, height: 24, borderRadius: '50%', background: agentColor(step.agent_type),
                color: '#fff', fontSize: 11, fontWeight: 700,
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>{i + 1}</div>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#111827', fontFamily: 'monospace' }}>
                  {step.name}
                </span>
                <span style={{
                  marginLeft: 8, fontSize: 11, padding: '1px 7px', borderRadius: 20,
                  background: agentColor(step.agent_type) + '18', color: agentColor(step.agent_type),
                  fontWeight: 700,
                }}>
                  {step.agent_type}
                </span>
              </div>
              {step.depends_on?.length > 0 && (
                <span style={{ fontSize: 11, color: '#9CA3AF' }}>
                  {'\u2190'} {step.depends_on.join(', ')}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Swarm recommendation */}
      {recommended_topology && (
        <div style={{
          padding: '14px 16px', borderRadius: 12, marginBottom: 20,
          background: 'rgba(236,72,153,0.06)', border: '1px solid rgba(236,72,153,0.25)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 16 }}>{'\uD83D\uDC1D'}</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#BE185D' }}>
              {lang === 'es' ? 'Recomendación de Swarm' : 'Swarm Recommendation'}
            </span>
            <span style={{
              padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700,
              background: 'rgba(236,72,153,0.15)', color: '#EC4899', textTransform: 'capitalize',
            }}>
              {recommended_topology}
            </span>
          </div>
          {topology_reason && (
            <p style={{ fontSize: 12, color: '#6B7280', margin: 0, lineHeight: 1.5 }}>
              {topology_reason}
            </p>
          )}
        </div>
      )}

      {/* Dashboard preview mockup */}
      <div style={{ marginBottom: 8 }}>
        <p style={{ fontSize: 12, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 10 }}>
          {t('dashboardPreview', lang)}
        </p>
        <DashboardPreviewMockup type={dashType} lang={lang} />
      </div>
    </div>
  )
}

// ── Step 4: Publish ──────────────────────────────────────────────────────────

function StepPublish({ workflow, publishing, automationType, lang = 'en' }) {
  const icon = TYPE_ICON_MAP[automationType] || '\u26A1'
  return (
    <div style={{ textAlign: 'center', padding: '20px 0' }}>
      <div style={{
        width: 80, height: 80, borderRadius: '50%',
        background: 'linear-gradient(135deg, #6366F1, #818CF8)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 20px', fontSize: 36,
      }}>
        {icon}
      </div>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        {t('step4Title', lang)}
      </h2>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 8, maxWidth: 440, margin: '0 auto' }}>
        {t('step4Desc', lang)}
      </p>
      {workflow && (
        <p style={{ fontSize: 14, color: '#374151', marginTop: 12, marginBottom: 0 }}>
          <strong>{workflow.name}</strong> {'\u2014'} {workflow.steps?.length || 0} {t('stepsLabel', lang)}
        </p>
      )}
      {publishing && (
        <div style={{ marginTop: 24 }}>
          <div style={{
            width: 40, height: 40, borderRadius: '50%', margin: '0 auto 12px',
            border: '3px solid #E5E7EB', borderTopColor: '#6366F1',
            animation: 'wizardSpin 0.8s linear infinite',
          }} />
          <style>{`@keyframes wizardSpin { to { transform: rotate(360deg) } }`}</style>
          <p style={{ fontSize: 13, color: '#6366F1', fontWeight: 600 }}>
            {t('publishing', lang)}
          </p>
        </div>
      )}
    </div>
  )
}

// ── Main wizard ──────────────────────────────────────────────────────────────

export default function WizardPage({ lang = 'en', onNavigate, onNavigateToBuilder, onNavigateToAutomation }) {
  const [step, setStep] = useState(0)
  const [description, setDescription] = useState('')
  const [customName, setCustomName] = useState('')
  const [automationType, setAutomationType] = useState('custom')
  const [inputType, setInputType] = useState('text')
  const [outputTypes, setOutputTypes] = useState(['dashboard'])
  const [workflow, setWorkflow] = useState(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [error, setError] = useState(null)
  const [skippedInputOutput, setSkippedInputOutput] = useState(false) // true when defaults were auto-applied

  const workflowRef = useRef(workflow)
  useEffect(() => { workflowRef.current = workflow }, [workflow])

  const handleToggleOutput = useCallback((key) => {
    setOutputTypes(prev => {
      if (prev.includes(key)) {
        // Don't allow removing all outputs
        if (prev.length <= 1) return prev
        return prev.filter(k => k !== key)
      }
      return [...prev, key]
    })
  }, [])

  const handleUpdateName = (newName) => {
    setCustomName(newName)
    if (workflow) setWorkflow({ ...workflow, name: newName })
  }

  // Generate workflow via API (between step 0 and step 1)
  const generateWorkflow = async () => {
    setIsGenerating(true)
    setError(null)

    try {
      const res = await fetchAPI('/wizard/generate', {
        method: 'POST',
        body: JSON.stringify({
          description,
          industry: null,
          complexity: 'medium',
          language: lang,
        }),
      })

      if (res.error) {
        setError(res.error)
        setIsGenerating(false)
        return false
      }

      const wf = res.data?.workflow || null
      if (wf) {
        wf.name = customName.trim() || description.trim().slice(0, 60) || wf.name
      }
      setWorkflow(wf)
      setIsGenerating(false)
      return true
    } catch (e) {
      setError(e.message)
      setIsGenerating(false)
      return false
    }
  }

  const handleNext = async () => {
    setError(null)

    if (step === 0) {
      if (!description.trim() || description.trim().length < 10) {
        setError(lang === 'es' ? 'Describe tu automatización (mínimo 10 caracteres)' : 'Describe your automation (minimum 10 characters)')
        return
      }
      if (!customName.trim()) {
        setError(lang === 'es' ? 'Ingresa un nombre para el flujo' : 'Enter a name for the workflow')
        return
      }
      // Generate workflow
      const ok = await generateWorkflow()
      if (!ok) return

      // Smart defaults: if predefined type, auto-fill input/output and skip to preview
      const defaults = QUICK_TYPE_DEFAULTS[automationType]
      if (defaults && defaults.input && automationType !== 'custom') {
        setInputType(defaults.input)
        setOutputTypes(defaults.outputs.length > 0 ? defaults.outputs : ['dashboard'])
        setSkippedInputOutput(true)
        setStep(3) // Jump directly to Preview
      } else {
        setSkippedInputOutput(false)
        setStep(1)
      }
      return
    }

    if (step === 1) {
      setStep(2)
      return
    }

    if (step === 2) {
      if (outputTypes.length === 0) {
        setError(lang === 'es' ? 'Selecciona al menos un destino de salida' : 'Select at least one output destination')
        return
      }
      setStep(3)
      return
    }

    if (step === 3) {
      setStep(4)
      return
    }
  }

  const handleBack = () => {
    if (step === 3 && skippedInputOutput) {
      // Go back to step 0 if we skipped input/output
      setStep(0)
      setSkippedInputOutput(false)
      return
    }
    if (step > 0) setStep(s => s - 1)
  }

  // Handler: user wants to change auto-selected input/output from Preview
  const handleChangeInputOutput = () => {
    setSkippedInputOutput(false)
    setStep(1) // Go to input selection step
  }

  // Publish: create workflow + automation, then navigate to dashboard
  const handlePublish = async () => {
    if (!workflow || publishing) return
    setPublishing(true)
    setError(null)

    try {
      // 1. Save workflow
      const currentWf = workflowRef.current || workflow
      const wfBody = {
        name: customName.trim() || currentWf.name || 'AI Generated Workflow',
        description: currentWf.description || description,
        dag_definition: {
          steps: (currentWf.steps || []).map(s => ({
            name: s.name,
            type: s.agent_type || s.type,
            depends_on: s.depends_on || [],
          })),
        },
      }

      const wfRes = await fetchAPI('/workflows/', {
        method: 'POST',
        body: JSON.stringify(wfBody),
      })

      if (wfRes.error) {
        setError(wfRes.error)
        setPublishing(false)
        return
      }

      const workflowId = wfRes.data?.id
      if (!workflowId) {
        setError(lang === 'es' ? 'No se pudo crear el workflow' : 'Failed to create workflow')
        setPublishing(false)
        return
      }

      // 2. Create automation
      const autoBody = {
        workflow_id: workflowId,
        name: customName.trim() || currentWf.name || 'AI Automation',
        trigger_type: inputType === 'webhook' ? 'webhook' : 'manual',
        icon: TYPE_ICON_MAP[automationType] || '\u26A1',
        color: TYPE_COLOR_MAP[automationType] || '#6366F1',
        input_config: { type: inputType },
        output_config: { destinations: outputTypes },
        dashboard_type: DASHBOARD_TYPE_MAP[automationType] || 'generic',
      }

      const autoRes = await fetchAPI('/automations/', {
        method: 'POST',
        body: JSON.stringify(autoBody),
      })

      if (autoRes.error) {
        // Automation creation failed, but workflow was created — still navigate
        console.warn('Automation creation failed:', autoRes.error)
      }

      const automationId = autoRes.data?.id

      setPublishing(false)

      // 3. Navigate to dashboard
      if (automationId && onNavigateToAutomation) {
        onNavigateToAutomation(automationId)
      } else if (onNavigate) {
        onNavigate('automations')
      }
    } catch (e) {
      setError(e.message)
      setPublishing(false)
    }
  }

  const canNext =
    step === 0 ? description.trim().length >= 10 && customName.trim().length > 0
    : step === 1 ? !!inputType
    : step === 2 ? outputTypes.length > 0
    : step === 3 ? !!workflow
    : false

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out', maxWidth: 700, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 8 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          {t('title', lang)}
        </h1>
        <p style={{ fontSize: 14, color: '#9CA3AF' }}>
          {t('subtitle', lang)}
        </p>
      </div>

      <div style={{
        background: '#fff', borderRadius: 16, border: '1px solid #E5E7EB',
        padding: 32, marginTop: 24,
      }}>
        <ProgressBar step={step} lang={lang} />

        {error && (
          <div style={{
            padding: '10px 14px', borderRadius: 8, marginBottom: 20, fontSize: 13,
            background: '#FEF2F2', border: '1px solid #FECACA', color: '#DC2626',
          }}>
            {error}
          </div>
        )}

        {/* Generating overlay (shown during API call from step 0) */}
        {isGenerating && <StepGenerating lang={lang} />}

        {/* Step content */}
        {!isGenerating && step === 0 && (
          <StepDescribe
            description={description}
            onChange={setDescription}
            workflowName={customName}
            onNameChange={setCustomName}
            selectedType={automationType}
            onTypeChange={setAutomationType}
            lang={lang}
          />
        )}
        {!isGenerating && step === 1 && (
          <StepInput selected={inputType} onSelect={setInputType} lang={lang} />
        )}
        {!isGenerating && step === 2 && (
          <StepOutput selected={outputTypes} onToggle={handleToggleOutput} lang={lang} />
        )}
        {!isGenerating && step === 3 && (
          <StepPreview
            workflow={workflow}
            inputType={inputType}
            outputTypes={outputTypes}
            automationType={automationType}
            onUpdateName={handleUpdateName}
            onChangeInputOutput={handleChangeInputOutput}
            skippedInputOutput={skippedInputOutput}
            lang={lang}
          />
        )}
        {!isGenerating && step === 4 && (
          <StepPublish
            workflow={workflow}
            publishing={publishing}
            automationType={automationType}
            lang={lang}
          />
        )}

        {/* Navigation */}
        {!isGenerating && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 32 }}>
            <button
              onClick={handleBack}
              disabled={step === 0}
              style={{
                padding: '10px 22px', borderRadius: 8, border: '1px solid #E5E7EB',
                background: '#fff', color: step === 0 ? '#D1D5DB' : '#6B7280',
                fontSize: 14, fontWeight: 500, cursor: step === 0 ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', gap: 6,
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <path d="M19 12H5M12 19l-7-7 7-7" />
              </svg>
              {t('back', lang)}
            </button>

            {step < 4 && (
              <button
                onClick={handleNext}
                disabled={!canNext || isGenerating}
                style={{
                  padding: '10px 28px', borderRadius: 8, border: 'none',
                  background: canNext && !isGenerating ? '#6366F1' : '#E5E7EB',
                  color: canNext && !isGenerating ? '#fff' : '#9CA3AF',
                  fontSize: 14, fontWeight: 600,
                  cursor: canNext && !isGenerating ? 'pointer' : 'not-allowed',
                  display: 'flex', alignItems: 'center', gap: 6,
                  transition: 'background 0.15s',
                }}
              >
                {step === 0 ? t('generateFlow', lang) : t('next', lang)}
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>
            )}

            {step === 4 && (
              <button
                onClick={handlePublish}
                disabled={publishing}
                style={{
                  padding: '12px 32px', borderRadius: 10, border: 'none',
                  background: publishing ? '#C7D2FE' : 'linear-gradient(135deg, #6366F1, #818CF8)',
                  color: '#fff', fontSize: 15, fontWeight: 700,
                  cursor: publishing ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', gap: 8,
                  transition: 'all 0.2s',
                  boxShadow: publishing ? 'none' : '0 4px 14px rgba(99,102,241,0.3)',
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                </svg>
                {publishing ? t('publishing', lang) : t('publish', lang)}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
