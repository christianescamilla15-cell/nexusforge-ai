import { useState } from 'react'
import { fetchAPI, DEMO_ENTERPRISE_RESULT, trackGuestRun } from '../../services/api'

const TEXTS = {
  es: {
    pageTitle: 'Asistente de Operaciones Empresariales',
    pageSubtitle: '8 agentes especializados procesan solicitudes de clientes en tiempo real.',
    heroDesc: 'Este caso de uso demuestra el motor NexusForge ejecutando un flujo empresarial real: clasificacion de intencion, consulta de documentos, reprogramacion de citas, actualizacion de CRM y generacion de respuestas.',
    formTitle: 'Enviar Solicitud',
    messageLabel: 'Mensaje',
    messagePlaceholder: 'Ej: Necesito reprogramar mi reunion del viernes...',
    customerLabel: 'ID de Cliente',
    customerPlaceholder: 'Ej: CUST-001',
    languageLabel: 'Idioma',
    priorityLabel: 'Prioridad',
    submit: 'Procesar Solicitud',
    processing: 'Procesando...',
    responseTitle: 'Resultado',
    statusLabel: 'Estado',
    intentLabel: 'Intencion',
    customerNameLabel: 'Cliente',
    responseMessageLabel: 'Respuesta',
    actionsLabel: 'Acciones Realizadas',
    documentsLabel: 'Documentos Consultados',
    crmLabel: 'CRM Actualizado',
    notificationLabel: 'Notificacion Enviada',
    timeLabel: 'Tiempo de Procesamiento',
    agentsLabel: 'Agentes Utilizados',
    yes: 'Si',
    no: 'No',
    pipelineTitle: 'Pipeline de 8 Agentes',
    pipelineSteps: [
      { agent: 'IntakeAgent', desc: 'Recibe solicitud y valida formato' },
      { agent: 'IntentClassifierAgent', desc: 'Clasifica intencion del cliente' },
      { agent: 'CustomerContextAgent', desc: 'Busca contexto del cliente en CRM' },
      { agent: 'DocumentRAGAgent', desc: 'Consulta base de conocimiento' },
      { agent: 'SchedulerAgent', desc: 'Reprograma citas si aplica' },
      { agent: 'CRMUpdateAgent', desc: 'Registra interaccion en CRM' },
      { agent: 'NotificationAgent', desc: 'Notifica al equipo interno' },
      { agent: 'SupervisorAgent', desc: 'Genera respuesta final coherente' },
    ],
    priorities: { low: 'Baja', normal: 'Normal', high: 'Alta', urgent: 'Urgente' },
    intentsSupported: 'Intenciones soportadas',
    intentsList: [
      'Reprogramar reunion',
      'Verificar contrato',
      'Consultar elegibilidad onboarding',
      'Consultar politica',
      'Actualizar CRM',
      'Consulta general',
    ],
    errorText: 'Error al procesar la solicitud. Verifica que el backend este activo.',
    sampleRequests: 'Solicitudes de Ejemplo',
    samples: [
      { message: 'Necesito reprogramar mi reunion del viernes', customer_id: 'CUST-001' },
      { message: 'Can you check my support coverage?', customer_id: 'CUST-004' },
      { message: 'Soy elegible para onboarding gratuito?', customer_id: 'CUST-005' },
    ],
    trySample: 'Probar',
  },
  en: {
    pageTitle: 'Enterprise Operations Assistant',
    pageSubtitle: '8 specialized agents process customer requests in real-time.',
    heroDesc: 'This use case demonstrates the NexusForge engine running a real enterprise workflow: intent classification, document lookup, meeting rescheduling, CRM updates, and response generation.',
    formTitle: 'Submit Request',
    messageLabel: 'Message',
    messagePlaceholder: 'Ex: I need to reschedule my Friday meeting...',
    customerLabel: 'Customer ID',
    customerPlaceholder: 'Ex: CUST-001',
    languageLabel: 'Language',
    priorityLabel: 'Priority',
    submit: 'Process Request',
    processing: 'Processing...',
    responseTitle: 'Result',
    statusLabel: 'Status',
    intentLabel: 'Intent',
    customerNameLabel: 'Customer',
    responseMessageLabel: 'Response',
    actionsLabel: 'Actions Taken',
    documentsLabel: 'Documents Consulted',
    crmLabel: 'CRM Updated',
    notificationLabel: 'Notification Sent',
    timeLabel: 'Processing Time',
    agentsLabel: 'Agents Used',
    yes: 'Yes',
    no: 'No',
    pipelineTitle: '8-Agent Pipeline',
    pipelineSteps: [
      { agent: 'IntakeAgent', desc: 'Receives request and validates format' },
      { agent: 'IntentClassifierAgent', desc: 'Classifies customer intent' },
      { agent: 'CustomerContextAgent', desc: 'Looks up customer context in CRM' },
      { agent: 'DocumentRAGAgent', desc: 'Queries knowledge base' },
      { agent: 'SchedulerAgent', desc: 'Reschedules meetings if applicable' },
      { agent: 'CRMUpdateAgent', desc: 'Logs interaction in CRM' },
      { agent: 'NotificationAgent', desc: 'Notifies internal team' },
      { agent: 'SupervisorAgent', desc: 'Generates final coherent response' },
    ],
    priorities: { low: 'Low', normal: 'Normal', high: 'High', urgent: 'Urgent' },
    intentsSupported: 'Supported Intents',
    intentsList: [
      'Reschedule meeting',
      'Verify contract',
      'Check onboarding eligibility',
      'Consult policy',
      'Update CRM',
      'General inquiry',
    ],
    errorText: 'Error processing the request. Verify the backend is running.',
    sampleRequests: 'Sample Requests',
    samples: [
      { message: 'I need to reschedule my Friday meeting', customer_id: 'CUST-001' },
      { message: 'Can you check my support coverage?', customer_id: 'CUST-004' },
      { message: 'Am I eligible for free onboarding?', customer_id: 'CUST-005' },
    ],
    trySample: 'Try',
  },
}

const cardStyle = {
  background: '#FFFFFF',
  border: '1px solid #E5E7EB',
  borderRadius: 12,
  padding: 24,
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
}

const labelStyle = {
  display: 'block',
  fontSize: 13,
  fontWeight: 600,
  color: '#374151',
  marginBottom: 6,
}

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 8,
  border: '1px solid #E5E7EB',
  background: '#F9FAFB',
  color: '#111827',
  fontSize: 14,
  outline: 'none',
  boxSizing: 'border-box',
  transition: 'border-color 0.15s',
}

const selectStyle = {
  ...inputStyle,
  cursor: 'pointer',
}

export default function EnterpriseOpsPage({ lang = 'es' }) {
  const currentLang = lang === 'en' ? 'en' : 'es'
  const txt = TEXTS[currentLang]

  const [message, setMessage] = useState('')
  const [customerId, setCustomerId] = useState('')
  const [language, setLanguage] = useState(currentLang)
  const [priority, setPriority] = useState('normal')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState(null)
  const [error, setError] = useState(null)
  const [isDemo, setIsDemo] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!message.trim()) return

    const { allowed, remaining } = trackGuestRun()
    if (!allowed) {
      setError(lang === 'es'
        ? 'Limite de prueba alcanzado (10 ejecuciones). Registrate para continuar.'
        : 'Trial limit reached (10 runs). Register to continue.')
      return
    }

    setLoading(true)
    setError(null)
    setResponse(null)
    setIsDemo(false)

    const result = await fetchAPI('/enterprise-ops/process', {
      method: 'POST',
      body: JSON.stringify({
        message: message.trim(),
        customer_id: customerId.trim() || null,
        language,
        priority,
      }),
    })

    if (result.error) {
      setError(result.error)
      setLoading(false)
      return
    }

    setResponse(result.data)
    setIsDemo(result.isDemo)
    setLoading(false)
  }

  const fillSample = (sample) => {
    setMessage(sample.message)
    setCustomerId(sample.customer_id || '')
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Hero */}
      <div style={{
        textAlign: 'center', padding: '40px 24px 36px', marginBottom: 28,
        background: '#FFFFFF', borderRadius: 16, border: '1px solid #E5E7EB',
        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          padding: '6px 16px', borderRadius: 100,
          background: 'rgba(37,99,235,0.06)', color: '#2563EB',
          fontSize: 13, fontWeight: 600, marginBottom: 16,
          border: '1px solid rgba(37,99,235,0.12)',
        }}>
          OPS
        </div>
        <h1 style={{
          fontSize: 28, fontWeight: 700, color: '#111827',
          lineHeight: 1.2, marginBottom: 10, letterSpacing: '-0.02em',
        }}>
          {txt.pageTitle}
        </h1>
        <p style={{ fontSize: 15, color: '#6B7280', marginBottom: 8 }}>
          {txt.pageSubtitle}
        </p>
        <p style={{
          fontSize: 14, color: '#4B5563', maxWidth: 640,
          margin: '0 auto', lineHeight: 1.6,
        }}>
          {txt.heroDesc}
        </p>
      </div>

      {/* Pipeline Steps */}
      <div style={{ ...cardStyle, marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginBottom: 16 }}>
          {txt.pipelineTitle}
        </h2>
        <div className="nxf-pipeline-grid" style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(240px, 100%), 1fr))',
          gap: 12,
        }}>
          {txt.pipelineSteps.map((step, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'flex-start', gap: 10,
              padding: '12px 14px', borderRadius: 8,
              border: '1px solid #E5E7EB', background: '#F9FAFB',
            }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%',
                background: '#2563EB', color: '#fff',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700, flexShrink: 0,
              }}>
                {i + 1}
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#111827', marginBottom: 2 }}>
                  {step.agent}
                </div>
                <div style={{ fontSize: 12, color: '#6B7280', lineHeight: 1.4 }}>
                  {step.desc}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="nxf-two-col-grid" style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.2fr)',
        gap: 24,
        alignItems: 'start',
      }}>
        {/* Left: Form */}
        <div>
          <div style={cardStyle}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginBottom: 20 }}>
              {txt.formTitle}
            </h2>

            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>{txt.messageLabel}</label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder={txt.messagePlaceholder}
                  rows={3}
                  style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }}
                  onFocus={(e) => e.target.style.borderColor = '#2563EB'}
                  onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
                  required
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>{txt.customerLabel}</label>
                <input
                  type="text"
                  value={customerId}
                  onChange={(e) => setCustomerId(e.target.value)}
                  placeholder={txt.customerPlaceholder}
                  style={inputStyle}
                  onFocus={(e) => e.target.style.borderColor = '#2563EB'}
                  onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
                <div>
                  <label style={labelStyle}>{txt.languageLabel}</label>
                  <select value={language} onChange={(e) => setLanguage(e.target.value)} style={selectStyle}>
                    <option value="es">Espanol</option>
                    <option value="en">English</option>
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>{txt.priorityLabel}</label>
                  <select value={priority} onChange={(e) => setPriority(e.target.value)} style={selectStyle}>
                    {Object.entries(txt.priorities).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !message.trim()}
                style={{
                  width: '100%', padding: '12px 20px', borderRadius: 8,
                  border: 'none', background: loading ? '#93C5FD' : '#2563EB',
                  color: '#fff', fontSize: 14, fontWeight: 600,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => { if (!loading) e.currentTarget.style.background = '#1D4ED8' }}
                onMouseLeave={(e) => { if (!loading) e.currentTarget.style.background = '#2563EB' }}
              >
                {loading ? txt.processing : txt.submit}
              </button>
            </form>

            {error && (
              <div style={{
                marginTop: 16, padding: '12px 14px', borderRadius: 8,
                background: '#FEF2F2', border: '1px solid #FECACA',
                color: '#DC2626', fontSize: 13,
              }}>
                {error}
              </div>
            )}
          </div>

          {/* Sample Requests */}
          <div style={{ ...cardStyle, marginTop: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 12 }}>
              {txt.sampleRequests}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {txt.samples.map((sample, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 12px', borderRadius: 8,
                  border: '1px solid #E5E7EB', background: '#F9FAFB',
                  gap: 10,
                }}>
                  <div style={{ fontSize: 13, color: '#374151', flex: 1 }}>
                    "{sample.message}"
                    {sample.customer_id && (
                      <span style={{ color: '#9CA3AF', marginLeft: 6 }}>({sample.customer_id})</span>
                    )}
                  </div>
                  <button
                    onClick={() => fillSample(sample)}
                    style={{
                      padding: '5px 12px', borderRadius: 6, border: '1px solid #E5E7EB',
                      background: '#fff', color: '#2563EB', fontSize: 12, fontWeight: 600,
                      cursor: 'pointer', flexShrink: 0, transition: 'all 0.15s',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(37,99,235,0.06)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = '#fff' }}
                  >
                    {txt.trySample}
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Supported Intents */}
          <div style={{ ...cardStyle, marginTop: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 10 }}>
              {txt.intentsSupported}
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {txt.intentsList.map((intent, i) => (
                <span key={i} style={{
                  padding: '4px 10px', borderRadius: 6, fontSize: 12,
                  background: 'rgba(37,99,235,0.06)', color: '#2563EB',
                  border: '1px solid rgba(37,99,235,0.12)', fontWeight: 500,
                }}>
                  {intent}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Response */}
        <div>
          {error && (
            <div style={{
              ...cardStyle, marginBottom: 16,
              background: 'rgba(220,38,38,0.04)', border: '1px solid rgba(220,38,38,0.2)',
            }}>
              <div style={{
                color: '#991B1B', fontSize: 14, lineHeight: 1.6,
                display: 'flex', alignItems: 'flex-start', gap: 10,
              }}>
                <span style={{ flexShrink: 0, fontSize: 16 }}>{'\u274C'}</span>
                <div>
                  <strong>Error:</strong> {error}
                </div>
              </div>
            </div>
          )}
          {response ? (
            <div style={cardStyle}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <h2 style={{ fontSize: 16, fontWeight: 700, color: '#111827', margin: 0 }}>
                  {txt.responseTitle}
                </h2>
                {isDemo && (
                  <span style={{
                    padding: '3px 10px', borderRadius: 6, fontSize: 11,
                    background: 'rgba(245,158,11,0.08)', color: '#D97706',
                    border: '1px solid rgba(245,158,11,0.2)',
                    fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 5,
                  }}>
                    <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#D97706' }} />
                    {currentLang === 'es' ? 'Modo Demo' : 'Demo Mode'}
                  </span>
                )}
              </div>

              {/* Status + Intent */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                <div style={{
                  padding: '12px 14px', borderRadius: 8,
                  background: response.status === 'completed' ? '#F0FDF4' : '#FEF2F2',
                  border: `1px solid ${response.status === 'completed' ? '#BBF7D0' : '#FECACA'}`,
                }}>
                  <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>
                    {txt.statusLabel}
                  </div>
                  <div style={{
                    fontSize: 14, fontWeight: 600,
                    color: response.status === 'completed' ? '#16A34A' : '#DC2626',
                  }}>
                    {response.status}
                  </div>
                </div>
                <div style={{
                  padding: '12px 14px', borderRadius: 8,
                  background: '#EFF6FF', border: '1px solid #BFDBFE',
                }}>
                  <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>
                    {txt.intentLabel}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#2563EB' }}>
                    {response.intent}
                  </div>
                </div>
              </div>

              {/* Customer */}
              {response.customer_name && (
                <div style={{
                  padding: '10px 14px', borderRadius: 8, marginBottom: 16,
                  background: '#F9FAFB', border: '1px solid #E5E7EB',
                }}>
                  <span style={{ fontSize: 12, color: '#6B7280', fontWeight: 600 }}>
                    {txt.customerNameLabel}:
                  </span>{' '}
                  <span style={{ fontSize: 14, color: '#111827', fontWeight: 500 }}>
                    {response.customer_name}
                  </span>
                </div>
              )}

              {/* Response Message */}
              <div style={{
                padding: '16px', borderRadius: 8, marginBottom: 16,
                background: '#F9FAFB', border: '1px solid #E5E7EB',
              }}>
                <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
                  {txt.responseMessageLabel}
                </div>
                <div style={{ fontSize: 14, color: '#111827', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                  {response.response_message}
                </div>
              </div>

              {/* Actions Timeline */}
              {response.actions_taken && response.actions_taken.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
                    {txt.actionsLabel}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {response.actions_taken.map((action, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: '8px 12px', borderRadius: 6,
                        background: '#F9FAFB', border: '1px solid #E5E7EB',
                      }}>
                        <div style={{
                          width: 22, height: 22, borderRadius: '50%',
                          background: 'rgba(37,99,235,0.08)', color: '#2563EB',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 10, fontWeight: 700, flexShrink: 0,
                        }}>
                          {i + 1}
                        </div>
                        <span style={{ fontSize: 13, color: '#374151', fontFamily: 'monospace' }}>
                          {action}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Documents */}
              {response.documents_consulted && response.documents_consulted.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
                    {txt.documentsLabel}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {response.documents_consulted.map((doc, i) => (
                      <span key={i} style={{
                        padding: '4px 10px', borderRadius: 6, fontSize: 12,
                        background: '#FEF9C3', border: '1px solid #FDE68A',
                        color: '#92400E', fontWeight: 500,
                      }}>
                        {doc}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Metadata row */}
              <div className="nxf-metadata-grid" style={{
                display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8,
                marginBottom: 16,
              }}>
                {[
                  { label: txt.crmLabel, value: response.crm_updated ? txt.yes : txt.no, color: response.crm_updated ? '#16A34A' : '#9CA3AF' },
                  { label: txt.notificationLabel, value: response.notification_sent ? txt.yes : txt.no, color: response.notification_sent ? '#16A34A' : '#9CA3AF' },
                  { label: txt.timeLabel, value: response.processing_time_ms ? `${response.processing_time_ms}ms` : '--', color: '#111827' },
                  { label: txt.agentsLabel, value: response.agents_used ? response.agents_used.length : 0, color: '#2563EB' },
                ].map((item, i) => (
                  <div key={i} style={{
                    padding: '10px 8px', borderRadius: 8, textAlign: 'center',
                    background: '#F9FAFB', border: '1px solid #E5E7EB',
                  }}>
                    <div style={{ fontSize: 10, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>
                      {item.label}
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: item.color }}>
                      {item.value}
                    </div>
                  </div>
                ))}
              </div>

              {/* Agents Used */}
              {response.agents_used && response.agents_used.length > 0 && (
                <div>
                  <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
                    {txt.agentsLabel}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {response.agents_used.map((agent, i) => (
                      <span key={i} style={{
                        padding: '4px 10px', borderRadius: 6, fontSize: 12,
                        background: 'rgba(37,99,235,0.06)', color: '#2563EB',
                        border: '1px solid rgba(37,99,235,0.12)', fontWeight: 500,
                      }}>
                        {agent}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{
              ...cardStyle, textAlign: 'center', padding: '60px 24px',
              color: '#9CA3AF',
            }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}>
                  <path d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 3.71a.75.75 0 01-.625.334H8.095a.75.75 0 01-.625-.334L5 14.5m14 0H5" />
                </svg>
              </div>
              <p style={{ fontSize: 14 }}>
                {currentLang === 'es'
                  ? 'Envia una solicitud para ver el resultado del pipeline de 8 agentes.'
                  : 'Submit a request to see the 8-agent pipeline result.'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
