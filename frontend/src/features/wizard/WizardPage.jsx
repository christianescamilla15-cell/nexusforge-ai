import { useState, useCallback } from 'react'
import { fetchAPI } from '../../services/api'

// ── Agent color map ───────────────────────────────────────────────────────────

// ── Translations ─────────────────────────────────────────────────────────────

const T = {
  steps: { es: ['Describir', 'Clarificar', 'Generando', 'Vista previa', 'Lanzar'], en: ['Describe', 'Clarify', 'Generating', 'Preview', 'Launch'] },
  title: { es: 'Asistente de Flujos de Trabajo IA', en: 'AI Workflow Wizard' },
  subtitle: { es: 'Describe lo que quieres automatizar — la IA diseña el flujo por ti.', en: 'Describe what you want to automate — the AI designs the workflow for you.' },
  step1Title: { es: '¿Qué quieres automatizar?', en: 'What do you want to automate?' },
  step1Desc: { es: 'Describe tu flujo de trabajo en lenguaje natural. La IA diseñará el pipeline óptimo de agentes.', en: 'Describe your workflow in plain language. The AI will design the optimal agent pipeline.' },
  step1Placeholder: { es: 'Ej: Leer correos de Gmail, clasificar por urgencia, resumir cada uno y enviar un resumen diario a Slack...', en: 'e.g. Read emails from Gmail, classify them by urgency, summarize each one, and send a daily digest to Slack...' },
  step1Examples: {
    es: ['Clasificar correos de clientes y enrutarlos al equipo correcto', 'Extraer datos de facturas PDF y guardar en Notion', 'Monitorear noticias sobre competidores y enviar alertas a Slack', 'Traducir documentos del español al inglés y resumir puntos clave'],
    en: ['Classify incoming customer emails and route them to the right team', 'Extract data from PDF invoices and save to Notion database', 'Monitor news articles for competitor mentions and send Slack alerts', 'Translate documents from Spanish to English and summarize key points'],
  },
  characters: { es: 'caracteres', en: 'characters' },
  examples: { es: 'Ejemplos:', en: 'Examples:' },
  next: { es: 'Siguiente', en: 'Next' },
  back: { es: 'Atrás', en: 'Back' },
  minChars: { es: 'Mínimo 10 caracteres', en: 'Minimum 10 characters' },
  step2Title: { es: 'Cuéntanos más', en: 'Tell us more' },
  step2Desc: { es: 'Responde estas preguntas para que la IA genere un flujo óptimo.', en: 'Answer these questions so the AI generates an optimal workflow.' },
  generating: { es: 'Generando tu flujo de trabajo...', en: 'Generating your workflow...' },
  generatingDesc: { es: 'La IA está seleccionando los mejores agentes y diseñando las dependencias...', en: 'The AI is selecting the best agents and designing dependencies...' },
  step4Title: { es: 'Tu flujo de trabajo', en: 'Your workflow' },
  step4Desc: { es: 'Revisa el flujo generado por IA. Puedes editarlo después en el builder.', en: 'Review the AI-generated workflow. You can edit it later in the builder.' },
  steps_label: { es: 'Pasos', en: 'Steps' },
  deps: { es: 'Depende de:', en: 'Depends on:' },
  noDeps: { es: 'Inicio (sin dependencias)', en: 'Start (no dependencies)' },
  integrations: { es: 'Integraciones sugeridas', en: 'Suggested integrations' },
  inputs: { es: 'Entradas', en: 'Inputs' },
  outputs: { es: 'Salidas', en: 'Outputs' },
  estimate: { es: 'Estimación', en: 'Estimate' },
  tokens: { es: 'tokens', en: 'tokens' },
  testDemo: { es: 'Probar en Demo', en: 'Test in Demo' },
  saveConfig: { es: 'Guardar y Configurar', en: 'Save & Configure' },
  provider: { es: 'Proveedor', en: 'Provider' },
  warning: { es: 'Advertencia', en: 'Warning' },
}

const t = (key, lang) => (T[key] && T[key][lang]) || (T[key] && T[key].en) || key

const AGENT_COLORS = {
  classifier: '#2563EB', extractor: '#059669', summarizer: '#7C3AED',
  analyzer: '#D97706', enricher: '#0891B2', validator: '#DC2626',
  reporter: '#DB2777', repair: '#6366F1', normalizer: '#0D9488',
  researcher: '#B45309', translator: '#4F46E5', compliance: '#BE185D',
  monitor: '#0369A1', planner: '#9333EA', knowledge: '#1D4ED8',
  scraper: '#B91C1C', ocr: '#0F766E', sentiment: '#C2410C',
  scheduler: '#6D28D9', webhook: '#374151',
}
const agentColor = (t) => AGENT_COLORS[t] || '#6B7280'

// ── Progress bar ──────────────────────────────────────────────────────────────

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
              {i < step ? '✓' : i + 1}
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

// ── Step 1: Description ───────────────────────────────────────────────────────

function StepDescribe({ description, onChange, lang = 'en' }) {
  const examples = T.step1Examples[lang] || T.step1Examples.en
  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        {t('step1Title', lang)}
      </h2>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 24 }}>
        {t('step1Desc', lang)}
      </p>
      <textarea
        value={description}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t('step1Placeholder', lang)}
        rows={5}
        autoFocus
        style={{
          width: '100%', padding: '14px 16px', borderRadius: 10, fontSize: 14,
          border: '2px solid #E5E7EB', outline: 'none', resize: 'vertical',
          lineHeight: 1.6, boxSizing: 'border-box', fontFamily: 'inherit',
          transition: 'border-color 0.15s',
        }}
        onFocus={(e) => e.target.style.borderColor = '#6366F1'}
        onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
      />
      <p style={{ fontSize: 12, color: '#9CA3AF', marginTop: 8, marginBottom: 20 }}>
        {description.length} {t('characters', lang)}
      </p>
      <p style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', marginBottom: 10 }}>{t('examples', lang)}</p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {examples.map((ex) => (
          <button
            key={ex}
            onClick={() => onChange(ex)}
            style={{
              textAlign: 'left', padding: '10px 14px', borderRadius: 8, fontSize: 13,
              border: '1px solid #E5E7EB', background: description === ex ? '#EEF2FF' : '#F9FAFB',
              color: description === ex ? '#6366F1' : '#374151', cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Step 2: Clarifying questions ──────────────────────────────────────────────

function StepClarify({ questions, answers, onChange, lang = 'en' }) {
  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        {t('step2Title', lang)}
      </h2>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 28 }}>
        {t('step2Desc', lang)}
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {questions.map((q) => (
          <div key={q.id}>
            <label style={{ fontSize: 14, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 8 }}>
              {q.question}
            </label>
            {q.type === 'text' && (
              <input
                type="text"
                value={answers[q.id] || ''}
                onChange={(e) => onChange(q.id, e.target.value)}
                style={{
                  width: '100%', padding: '10px 14px', borderRadius: 8, fontSize: 14,
                  border: '1px solid #E5E7EB', outline: 'none', boxSizing: 'border-box',
                }}
                onFocus={(e) => e.target.style.borderColor = '#6366F1'}
                onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
              />
            )}
            {q.type === 'select' && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {q.options.map((opt) => (
                  <button
                    key={opt}
                    onClick={() => onChange(q.id, opt)}
                    style={{
                      padding: '7px 14px', borderRadius: 20, fontSize: 13, cursor: 'pointer',
                      border: '1px solid',
                      borderColor: answers[q.id] === opt ? '#6366F1' : '#E5E7EB',
                      background: answers[q.id] === opt ? '#EEF2FF' : '#fff',
                      color: answers[q.id] === opt ? '#6366F1' : '#374151',
                      fontWeight: answers[q.id] === opt ? 600 : 400,
                      transition: 'all 0.15s',
                    }}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            )}
            {q.type === 'multiselect' && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {q.options.map((opt) => {
                  const selected = (answers[q.id] || []).includes(opt)
                  return (
                    <button
                      key={opt}
                      onClick={() => {
                        const cur = answers[q.id] || []
                        onChange(q.id, selected ? cur.filter((v) => v !== opt) : [...cur, opt])
                      }}
                      style={{
                        padding: '7px 14px', borderRadius: 20, fontSize: 13, cursor: 'pointer',
                        border: '1px solid',
                        borderColor: selected ? '#059669' : '#E5E7EB',
                        background: selected ? '#F0FDF4' : '#fff',
                        color: selected ? '#059669' : '#374151',
                        fontWeight: selected ? 600 : 400,
                        transition: 'all 0.15s',
                      }}
                    >
                      {selected ? '✓ ' : ''}{opt}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Step 3: Generating ────────────────────────────────────────────────────────

function StepGenerating({ lang = 'en' }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 0' }}>
      <div style={{
        width: 64, height: 64, borderRadius: '50%', margin: '0 auto 24px',
        border: '4px solid #E5E7EB', borderTopColor: '#6366F1',
        animation: 'spin 0.8s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        {t('generating', lang)}
      </h2>
      <p style={{ fontSize: 14, color: '#9CA3AF' }}>
        {t('generatingDesc', lang)}
      </p>
    </div>
  )
}

// ── Step 4: Preview ───────────────────────────────────────────────────────────

function StepPreview({ workflow, warning, lang = 'en', onUpdateName, onSaveDraft, onOpenBuilder, savingDraft }) {
  if (!workflow) return null
  const { name, description, steps = [], suggested_integrations = {}, estimated_tokens, estimated_cost_usd } = workflow

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
        {lang === 'es' ? 'Tu flujo de trabajo está listo' : 'Your workflow is ready'}
      </h2>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 24 }}>{description}</p>

      {warning && (
        <div style={{
          padding: '10px 14px', borderRadius: 8, marginBottom: 20, fontSize: 13,
          background: '#FFFBEB', border: '1px solid #FDE68A', color: '#92400E',
        }}>
          {warning}
        </div>
      )}

      {/* Editable workflow name */}
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
        <span style={{ fontSize: 12, color: '#6366F1', flexShrink: 0 }}>
          ~{estimated_tokens} tokens · ~${(estimated_cost_usd || 0).toFixed(4)}
        </span>
      </div>

      {/* Action buttons: Save Draft + Open Builder */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        <button
          onClick={onSaveDraft}
          disabled={savingDraft}
          style={{
            padding: '8px 16px', borderRadius: 8, border: '1px solid #E5E7EB',
            background: '#fff', color: '#6B7280', fontSize: 13, fontWeight: 600,
            cursor: savingDraft ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" />
            <polyline points="17 21 17 13 7 13 7 21" />
            <polyline points="7 3 7 8 15 8" />
          </svg>
          {savingDraft
            ? (lang === 'es' ? 'Guardando...' : 'Saving...')
            : (lang === 'es' ? 'Guardar como Borrador' : 'Save as Draft')
          }
        </button>
        <button
          onClick={onOpenBuilder}
          style={{
            padding: '8px 16px', borderRadius: 8, border: '1px solid #6366F1',
            background: '#EEF2FF', color: '#6366F1', fontSize: 13, fontWeight: 600,
            cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
          {lang === 'es' ? 'Editar en Builder' : 'Edit in Builder'}
        </button>
      </div>

      {/* Steps */}
      <div style={{ marginBottom: 24 }}>
        <p style={{ fontSize: 12, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 12 }}>
          Pipeline ({steps.length} {lang === 'es' ? 'pasos' : 'steps'})
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
                  ← {step.depends_on.join(', ')}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Suggested integrations */}
      {(suggested_integrations.inputs?.length > 0 || suggested_integrations.outputs?.length > 0) && (
        <div style={{ padding: '14px 16px', borderRadius: 10, background: '#F0FDF4', border: '1px solid #BBF7D0' }}>
          <p style={{ fontSize: 12, fontWeight: 700, color: '#16A34A', marginBottom: 8 }}>
            {lang === 'es' ? 'Integraciones sugeridas' : 'Suggested Integrations'}
          </p>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13 }}>
            {suggested_integrations.inputs?.length > 0 && (
              <div>
                <span style={{ color: '#6B7280', fontWeight: 600 }}>{lang === 'es' ? 'Entradas: ' : 'Inputs: '}</span>
                <span style={{ color: '#374151' }}>{suggested_integrations.inputs.join(', ')}</span>
              </div>
            )}
            {suggested_integrations.outputs?.length > 0 && (
              <div>
                <span style={{ color: '#6B7280', fontWeight: 600 }}>{lang === 'es' ? 'Salidas: ' : 'Outputs: '}</span>
                <span style={{ color: '#374151' }}>{suggested_integrations.outputs.join(', ')}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Step 5: Launch ────────────────────────────────────────────────────────────

function StepLaunch({ workflow, onDemo, onConfigure, executing, execResult, lang = 'en' }) {
  return (
    <div style={{ textAlign: 'center', padding: '20px 0' }}>
      <div style={{
        width: 72, height: 72, borderRadius: '50%', background: 'linear-gradient(135deg, #6366F1, #818CF8)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px',
      }}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round">
          <polygon points="5 3 19 12 5 21 5 3" />
        </svg>
      </div>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        {lang === 'es' ? 'Listo para lanzar' : 'Ready to launch'}
      </h2>
      <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 32, maxWidth: 400, margin: '0 auto 32px' }}>
        {lang === 'es'
          ? <>Tu flujo <strong>{workflow?.name}</strong> con {workflow?.steps?.length} pasos está listo. Elige cómo continuar.</>
          : <>Your <strong>{workflow?.name}</strong> workflow with {workflow?.steps?.length} steps is ready. Choose how to proceed.</>
        }
      </p>

      <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
        <button
          onClick={onDemo}
          disabled={executing}
          style={{
            padding: '14px 28px', borderRadius: 10, border: '2px solid #6366F1',
            background: '#EEF2FF', color: '#6366F1', fontSize: 15, fontWeight: 700,
            cursor: executing ? 'not-allowed' : 'pointer', minWidth: 200,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          {executing ? (lang === 'es' ? 'Ejecutando…' : 'Running…') : t('testDemo', lang)}
        </button>
        <button
          onClick={onConfigure}
          style={{
            padding: '14px 28px', borderRadius: 10, border: 'none',
            background: 'linear-gradient(135deg, #6366F1, #818CF8)', color: '#fff',
            fontSize: 15, fontWeight: 700, cursor: 'pointer', minWidth: 200,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
          </svg>
          {t('saveConfig', lang)}
        </button>
      </div>

      {execResult && (
        <div style={{
          marginTop: 24, padding: '12px 16px', borderRadius: 10, fontSize: 13,
          background: execResult.error ? '#FEF2F2' : '#F0FDF4',
          border: `1px solid ${execResult.error ? '#FECACA' : '#BBF7D0'}`,
          color: execResult.error ? '#DC2626' : '#16A34A',
          maxWidth: 480, margin: '24px auto 0',
        }}>
          {execResult.error ? `Error: ${execResult.error}` : '✓ Execution started successfully'}
        </div>
      )}
    </div>
  )
}

// ── Main wizard ───────────────────────────────────────────────────────────────

export default function WizardPage({ lang = 'en', onNavigate, onNavigateToBuilder }) {
  const [step, setStep] = useState(0)
  const [description, setDescription] = useState('')
  const [questions, setQuestions] = useState([])
  const [answers, setAnswers] = useState({})
  const [workflow, setWorkflow] = useState(null)
  const [warning, setWarning] = useState(null)
  const [executing, setExecuting] = useState(false)
  const [execResult, setExecResult] = useState(null)
  const [error, setError] = useState(null)

  const handleAnswer = useCallback((id, value) => {
    setAnswers((prev) => ({ ...prev, [id]: value }))
  }, [])

  const handleNext = async () => {
    setError(null)

    if (step === 0) {
      if (!description.trim()) { setError('Please describe your workflow first.'); return }
      // Fetch clarifying questions
      const res = await fetchAPI('/wizard/questions', {
        method: 'POST',
        body: JSON.stringify({ description, language: lang }),
      })
      if (res.error) { setError(res.error); return }
      setQuestions(res.data?.questions || [])
      setStep(1)
      return
    }

    if (step === 1) {
      // Move to generating step, then call API
      setStep(2)
      const complexity = answers.complexity?.includes('3') ? 'simple'
        : answers.complexity?.includes('7') ? 'complex' : 'medium'
      const res = await fetchAPI('/wizard/generate', {
        method: 'POST',
        body: JSON.stringify({
          description,
          industry: answers.industry || null,
          complexity,
          language: lang,
        }),
      })
      if (res.error) { setError(res.error); setStep(1); return }
      setWorkflow(res.data?.workflow || null)
      setWarning(res.data?.warning || null)
      setStep(3)
      return
    }

    if (step === 3) { setStep(4); return }
  }

  const handleBack = () => {
    if (step === 2) return // can't go back while generating
    if (step > 0) setStep((s) => s - 1)
  }

  const handleDemo = async () => {
    if (!workflow) return
    setExecuting(true)
    setError(null)

    try {
      // Step 1: Save workflow first
      const saveRes = await fetchAPI('/workflows', {
        method: 'POST',
        body: JSON.stringify({
          name: workflow.name || 'AI Generated Workflow',
          description: workflow.description || description,
          dag_definition: {
            steps: (workflow.steps || []).map(s => ({
              name: s.name,
              type: s.agent_type || s.type,
              depends_on: s.depends_on || [],
            })),
          },
        }),
      })

      if (saveRes.error || !saveRes.data) {
        // If save fails, try direct enterprise-ops as fallback demo
        const fallbackRes = await fetchAPI('/enterprise-ops/process', {
          method: 'POST',
          body: JSON.stringify({
            message: description,
            customer_id: 'WIZARD-001',
            language: lang,
          }),
        })
        setExecResult(fallbackRes)
        setExecuting(false)
        return
      }

      // Step 2: Execute with the saved workflow ID
      const workflowId = saveRes.data.id
      const execRes = await fetchAPI('/executions', {
        method: 'POST',
        body: JSON.stringify({
          workflow_id: workflowId,
          trigger_type: 'manual',
          input_data: { source: 'wizard', description },
        }),
      })
      setExecResult(execRes)
    } catch (e) {
      setError(e.message)
    }
    setExecuting(false)
  }

  const handleConfigure = async () => {
    // Save workflow first, then open in builder with the saved ID
    if (workflow) {
      const saveRes = await fetchAPI('/workflows', {
        method: 'POST',
        body: JSON.stringify({
          name: workflow.name || 'AI Generated Workflow',
          description: workflow.description || description,
          dag_definition: {
            steps: (workflow.steps || []).map(s => ({
              name: s.name,
              type: s.agent_type || s.type,
              depends_on: s.depends_on || [],
            })),
          },
        }),
      })

      if (saveRes.data?.id && onNavigateToBuilder) {
        onNavigateToBuilder(saveRes.data.id)
        return
      }
    }
    // Fallback: go to integrations if save failed or no builder callback
    if (onNavigate) onNavigate('integrations')
  }

  const [savingDraft, setSavingDraft] = useState(false)

  const handleUpdateName = (newName) => {
    if (workflow) setWorkflow({ ...workflow, name: newName })
  }

  const handleSaveDraft = async () => {
    if (!workflow) return
    setSavingDraft(true)
    const res = await fetchAPI('/workflows', {
      method: 'POST',
      body: JSON.stringify({
        name: workflow.name || 'Draft Workflow',
        description: workflow.description || description,
        dag_definition: {
          steps: (workflow.steps || []).map(s => ({
            name: s.name,
            type: s.agent_type || s.type,
            depends_on: s.depends_on || [],
          })),
        },
      }),
    })
    setSavingDraft(false)
    if (res.data?.id) {
      setError(null)
      alert(lang === 'es' ? `Borrador guardado (ID: ${res.data.id.slice(0,8)}...)` : `Draft saved (ID: ${res.data.id.slice(0,8)}...)`)
    } else {
      setError(res.error || (lang === 'es' ? 'Error al guardar borrador' : 'Failed to save draft'))
    }
  }

  const handleOpenBuilder = async () => {
    if (!workflow) return
    const res = await fetchAPI('/workflows', {
      method: 'POST',
      body: JSON.stringify({
        name: workflow.name || 'AI Generated Workflow',
        description: workflow.description || description,
        dag_definition: {
          steps: (workflow.steps || []).map(s => ({
            name: s.name,
            type: s.agent_type || s.type,
            depends_on: s.depends_on || [],
          })),
        },
      }),
    })
    if (res.data?.id && onNavigateToBuilder) {
      onNavigateToBuilder(res.data.id)
    }
  }

  const canNext = step === 0 ? description.trim().length > 10
    : step === 1 ? true
    : step === 3 ? !!workflow
    : false

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out', maxWidth: 680, margin: '0 auto' }}>
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

        {step === 0 && <StepDescribe description={description} onChange={setDescription} lang={lang} />}
        {step === 1 && <StepClarify questions={questions} answers={answers} onChange={handleAnswer} lang={lang} />}
        {step === 2 && <StepGenerating lang={lang} />}
        {step === 3 && <StepPreview workflow={workflow} warning={warning} lang={lang} onUpdateName={handleUpdateName} onSaveDraft={handleSaveDraft} onOpenBuilder={handleOpenBuilder} savingDraft={savingDraft} />}
        {step === 4 && (
          <StepLaunch
            workflow={workflow}
            onDemo={handleDemo}
            onConfigure={handleConfigure}
            executing={executing}
            execResult={execResult}
            lang={lang}
          />
        )}

        {/* Navigation */}
        {step !== 2 && (
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
                disabled={!canNext}
                style={{
                  padding: '10px 28px', borderRadius: 8, border: 'none',
                  background: canNext ? '#6366F1' : '#E5E7EB',
                  color: canNext ? '#fff' : '#9CA3AF',
                  fontSize: 14, fontWeight: 600, cursor: canNext ? 'pointer' : 'not-allowed',
                  display: 'flex', alignItems: 'center', gap: 6,
                  transition: 'background 0.15s',
                }}
              >
                {step === 1 ? (lang === 'es' ? 'Generar Flujo' : 'Generate Workflow') : step === 3 ? (lang === 'es' ? 'Continuar' : 'Continue') : t('next', lang)}
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
