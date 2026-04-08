import { useState, useRef, useEffect, useCallback } from 'react'
import { fetchAPI } from '../../services/api'
import useChatStream from './hooks/useChatStream'
import { usePreviewEvents, parseAssistantResponse } from './hooks/usePreviewEvents'

const QUICK_ACTIONS = [
  { icon: '\uD83C\uDFAB', labelEs: 'Clasificar tickets', labelEn: 'Classify tickets', prompt: { es: 'Quiero clasificar tickets de soporte automaticamente', en: 'I want to automatically classify support tickets' } },
  { icon: '\uD83D\uDCC4', labelEs: 'Analizar documentos', labelEn: 'Analyze documents', prompt: { es: 'Necesito analizar documentos y facturas automaticamente', en: 'I need to automatically analyze documents and invoices' } },
  { icon: '\uD83D\uDCE7', labelEs: 'Responder emails', labelEn: 'Reply to emails', prompt: { es: 'Quiero responder emails de clientes automaticamente', en: 'I want to automatically reply to customer emails' } },
  { icon: '\uD83D\uDCCA', labelEs: 'Generar reportes', labelEn: 'Generate reports', prompt: { es: 'Necesito generar reportes semanales automaticos', en: 'I need to generate automatic weekly reports' } },
  { icon: '\uD83D\uDCF1', labelEs: 'Monitorear redes', labelEn: 'Monitor social', prompt: { es: 'Quiero monitorear menciones de mi marca en redes sociales', en: 'I want to monitor brand mentions on social media' } },
  { icon: '\u2699\uFE0F', labelEs: 'Procesar datos', labelEn: 'Process data', prompt: { es: 'Necesito procesar y validar datos de multiples fuentes', en: 'I need to process and validate data from multiple sources' } },
  { icon: '\uD83D\uDD0D', labelEs: 'Investigar mercado', labelEn: 'Research market', prompt: { es: 'Necesito investigar tendencias de mercado y competencia', en: 'I need to research market trends and competition' } },
  { icon: '\uD83D\uDEE1\uFE0F', labelEs: 'Compliance check', labelEn: 'Compliance check', prompt: { es: 'Quiero verificar cumplimiento regulatorio de mis documentos', en: 'I want to check regulatory compliance of my documents' } },
  { icon: '\uD83E\uDD16', labelEs: 'Pipeline IA', labelEn: 'AI Pipeline', prompt: { es: 'Quiero crear un pipeline multi-agente personalizado', en: 'I want to create a custom multi-agent pipeline' } },
]

function ThinkingBubble({ thinking }) {
  const [expanded, setExpanded] = useState(false)
  const lines = thinking.split('\n').filter(l => l.trim())
  const preview = thinking.slice(-60)

  return (
    <div style={{ alignSelf: 'flex-start', maxWidth: expanded ? '85%' : 'auto' }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          background: expanded ? '#FFFBEB' : '#FEF3C7',
          color: '#92400E', padding: expanded ? '12px 16px' : '8px 14px',
          borderRadius: '14px 14px 14px 4px',
          fontSize: 12, fontStyle: 'italic',
          border: '1px solid #FDE68A',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          maxWidth: expanded ? '100%' : 340,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: expanded ? 8 : 0 }}>
          <span style={{ fontSize: 14, animation: 'pulse 1.5s infinite', flexShrink: 0 }}>{'\uD83E\uDDE0'}</span>
          {!expanded && (
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {preview}
            </span>
          )}
          {expanded && (
            <span style={{ fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Reasoning ({lines.length} lines) — click to collapse
            </span>
          )}
        </div>
        {expanded && (
          <div style={{
            maxHeight: 300, overflowY: 'auto', fontSize: 12,
            lineHeight: 1.6, whiteSpace: 'pre-wrap', marginTop: 4,
            padding: '8px 0', borderTop: '1px solid #FDE68A',
          }}>
            {thinking}
          </div>
        )}
      </div>
    </div>
  )
}

function formatMessage(text) {
  if (!text) return null
  return text.split('\n').map((line, i) => {
    // Bold
    const formatted = line.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    if (formatted !== line) {
      return <div key={i} dangerouslySetInnerHTML={{ __html: formatted }} style={{ marginBottom: 4 }} />
    }
    if (line.trim() === '') return <br key={i} />
    return <div key={i} style={{ marginBottom: 4 }}>{line}</div>
  })
}

export default function ChatPanel({ lang = 'es' }) {
  const chat = useChatStream(lang)
  const { emitPreview } = usePreviewEvents()
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const [publishing, setPublishing] = useState(false)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [chat.messages, chat.streaming, chat.currentResponse, chat.currentThinking, scrollToBottom])

  useEffect(() => {
    if (inputRef.current) inputRef.current.focus()
  }, [])

  // Welcome message
  useEffect(() => {
    if (chat.messages.length === 0) {
      chat.setMessages([{
        id: 'welcome',
        role: 'system',
        text: lang === 'es'
          ? '\u00A1Hola! Soy tu asistente de automatizaci\u00F3n. Desc\u00EDbeme qu\u00E9 proceso quieres automatizar y lo construyo paso a paso.'
          : 'Hi! I\u2019m your automation assistant. Describe what you want to automate and I\u2019ll build it step by step.',
      }])
    }
  }, [])

  // Emit preview events as assistant responds
  useEffect(() => {
    if (chat.currentResponse) {
      const event = parseAssistantResponse(chat.currentResponse, lang)
      if (event) emitPreview(event)
    }
  }, [chat.currentResponse, lang, emitPreview])

  // Detect publish confirmation and actually create the automation
  const publishAutomation = useCallback(async () => {
    if (publishing) return
    setPublishing(true)
    emitPreview({ type: 'building', data: {} })

    // Extract conversation summary for the workflow generator
    const conversationSummary = chat.messages
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => m.text)
      .join('\n')
      .slice(-2000)

    try {
      // Step 1: Generate workflow DAG via AI
      chat.setMessages(prev => [...prev, {
        id: `sys-${Date.now()}`, role: 'system',
        text: lang === 'es' ? '\u2699\uFE0F Generando workflow...' : '\u2699\uFE0F Generating workflow...',
      }])

      const genRes = await fetchAPI('/wizard/generate', {
        method: 'POST',
        body: JSON.stringify({
          description: conversationSummary,
          complexity: 'medium',
          language: lang,
        }),
      })

      const workflow = genRes.data?.workflow
      if (!workflow || genRes.error) {
        chat.setMessages(prev => [...prev, {
          id: `err-${Date.now()}`, role: 'assistant',
          text: lang === 'es'
            ? 'Hubo un error generando el workflow. Intenta describir tu automatizaci\u00F3n de nuevo.'
            : 'Error generating workflow. Try describing your automation again.',
        }])
        setPublishing(false)
        return
      }

      // Show DAG in preview as soon as we have the steps
      emitPreview({
        type: 'workflow',
        data: {
          name: workflow.name,
          steps: (workflow.steps || []).map(s => ({
            name: s.name,
            type: s.agent_type || s.type,
            depends_on: s.depends_on || [],
          })),
          runId: null, // no run yet — just show the DAG structure
        },
      })

      // Step 2: Save workflow
      chat.setMessages(prev => [...prev, {
        id: `sys2-${Date.now()}`, role: 'system',
        text: lang === 'es' ? '\uD83D\uDCBE Guardando workflow...' : '\uD83D\uDCBE Saving workflow...',
      }])

      const wfRes = await fetchAPI('/workflows/', {
        method: 'POST',
        body: JSON.stringify({
          name: workflow.name || 'AI Chat Workflow',
          description: workflow.description || conversationSummary.slice(0, 200),
          dag_definition: {
            steps: (workflow.steps || []).map(s => ({
              name: s.name,
              type: s.agent_type || s.type,
              depends_on: s.depends_on || [],
            })),
          },
        }),
      })

      if (wfRes.error || !wfRes.data?.id) {
        chat.setMessages(prev => [...prev, {
          id: `err2-${Date.now()}`, role: 'assistant',
          text: lang === 'es' ? 'Error guardando el workflow: ' + (wfRes.error || 'ID no recibido') : 'Error saving workflow.',
        }])
        setPublishing(false)
        return
      }

      // Step 3: Create automation
      chat.setMessages(prev => [...prev, {
        id: `sys3-${Date.now()}`, role: 'system',
        text: lang === 'es' ? '\uD83D\uDE80 Creando automatizaci\u00F3n...' : '\uD83D\uDE80 Creating automation...',
      }])

      // Extract config from conversation
      const inputs = workflow.suggested_integrations?.inputs || ['text']
      const outputs = workflow.suggested_integrations?.outputs || ['dashboard']
      const inputType = inputs[0] === 'drive' ? 'drive' : inputs[0] === 'gmail' ? 'email' : inputs[0] === 'webhook' ? 'webhook' : 'text'

      const autoRes = await fetchAPI('/automations/', {
        method: 'POST',
        body: JSON.stringify({
          workflow_id: wfRes.data.id,
          name: workflow.name || 'AI Automation',
          trigger_type: inputType === 'webhook' ? 'webhook' : 'manual',
          icon: '\u2728',
          color: '#6366F1',
          input_config: { type: inputType },
          output_config: { destinations: outputs },
          requires_approval: conversationSummary.toLowerCase().includes('aprobaci') || conversationSummary.toLowerCase().includes('approval'),
        }),
      })

      if (autoRes.error) {
        chat.setMessages(prev => [...prev, {
          id: `err3-${Date.now()}`, role: 'assistant',
          text: lang === 'es' ? 'Error creando la automatizaci\u00F3n: ' + autoRes.error : 'Error creating automation.',
        }])
        setPublishing(false)
        return
      }

      // Success — update preview with run_id if available for live WebSocket tracking
      const runId = autoRes.data?.run_id || autoRes.data?.id || null
      emitPreview({
        type: 'workflow',
        data: {
          name: workflow.name,
          steps: (workflow.steps || []).map(s => ({
            name: s.name,
            type: s.agent_type || s.type,
            depends_on: s.depends_on || [],
          })),
          runId,
        },
      })
      chat.setMessages(prev => [...prev, {
        id: `done-${Date.now()}`, role: 'assistant',
        text: lang === 'es'
          ? `\u2705 **\u00A1"${workflow.name}" est\u00E1 lista!**\n\nTu automatizaci\u00F3n fue creada con ${workflow.steps?.length || 0} agentes. Ve a **Automatizaciones** para ejecutarla o configurar los detalles.`
          : `\u2705 **"${workflow.name}" is ready!**\n\nYour automation was created with ${workflow.steps?.length || 0} agents. Go to **Automations** to run it or configure details.`,
      }])

    } catch (err) {
      chat.setMessages(prev => [...prev, {
        id: `exc-${Date.now()}`, role: 'assistant',
        text: lang === 'es' ? 'Error inesperado: ' + err.message : 'Unexpected error: ' + err.message,
      }])
    }
    setPublishing(false)
  }, [chat, lang, emitPreview, publishing])

  // Detect when user says "yes, publish" in any form
  const isPublishConfirmation = (text) => {
    const lower = text.toLowerCase().trim()
    const confirmWords = ['si', 's\u00ED', 'yes', 'publ', 'crear', 'create', 'listo', 'dale', 'ok', 'confirmo', 'hazlo', 'do it', 'go ahead', 'adelante', 'claro', 'por supuesto', 'vamos']
    return confirmWords.some(w => lower.startsWith(w) || lower === w)
  }

  // Check if assistant previously asked for confirmation (broad matching)
  const hasConfirmationPrompt = () => {
    return chat.messages.some(m => {
      if (m.role !== 'assistant') return false
      const t = m.text.toLowerCase()
      return t.includes('publico') || t.includes('publish') || t.includes('publicar') ||
             t.includes('cree el proyecto') || t.includes('crear este') || t.includes('creado') ||
             t.includes('est\u00e1 listo') || t.includes('is ready') || t.includes('comencemos') ||
             t.includes('listo para') || t.includes('\u00bfest\u00e1s listo') || t.includes('shall i create') ||
             t.includes('lo creo') || t.includes('configurar')
    })
  }

  const handleSend = (text) => {
    // Check if this is a publish confirmation
    if (isPublishConfirmation(text) && hasConfirmationPrompt()) {
      chat.setMessages(prev => [...prev, { id: `u-${Date.now()}`, role: 'user', text: text.trim() }])
      publishAutomation()
      return
    }

    chat.sendMessage(text, (fullText) => {
      const event = parseAssistantResponse(fullText, lang)
      if (event) emitPreview(event)
    })
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    handleSend(chat.input)
  }

  const showQuickActions = chat.messages.length <= 1 && !chat.streaming

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: '#FAFBFC', width: '100%',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #E5E7EB',
        background: '#fff', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontSize: 18,
          }}>
            {'\u2728'}
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#111827' }}>
              {lang === 'es' ? 'Asistente IA' : 'AI Assistant'}
            </div>
            <div style={{ fontSize: 11, color: chat.streaming ? '#059669' : '#9CA3AF' }}>
              {chat.streaming
                ? (chat.isThinking
                  ? (lang === 'es' ? '\uD83E\uDDE0 Razonando...' : '\uD83E\uDDE0 Reasoning...')
                  : (lang === 'es' ? 'Escribiendo...' : 'Typing...'))
                : (chat.provider || (lang === 'es' ? 'Listo para ayudarte' : 'Ready to help'))}
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1, overflow: 'auto', padding: '16px 20px',
        display: 'flex', flexDirection: 'column', gap: 12,
      }}>
        {chat.messages.map(msg => {
          if (msg.role === 'system') {
            return (
              <div key={msg.id} style={{
                textAlign: 'center', fontSize: 13, color: '#9CA3AF',
                padding: '8px 0',
              }}>
                {msg.text}
              </div>
            )
          }

          if (msg.role === 'user') {
            return (
              <div key={msg.id} style={{
                alignSelf: 'flex-end', maxWidth: '80%',
              }}>
                <div style={{
                  background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
                  color: '#fff', padding: '12px 16px',
                  borderRadius: '18px 18px 4px 18px',
                  fontSize: 14, lineHeight: 1.5,
                }}>
                  {msg.text}
                </div>
              </div>
            )
          }

          // Assistant message
          return (
            <div key={msg.id} style={{ alignSelf: 'flex-start', maxWidth: '85%' }}>
              {msg.thinking && (
                <details style={{
                  marginBottom: 6, background: '#FFFBEB', borderRadius: 12,
                  border: '1px solid #FDE68A', overflow: 'hidden',
                }}>
                  <summary style={{
                    padding: '8px 14px', fontSize: 12, fontWeight: 600,
                    color: '#B45309', cursor: 'pointer',
                  }}>
                    {'\uD83E\uDDE0'} {lang === 'es' ? 'Ver razonamiento' : 'View reasoning'}
                  </summary>
                  <div style={{
                    padding: '8px 14px', fontSize: 12, color: '#92400E',
                    lineHeight: 1.5, fontStyle: 'italic', maxHeight: 200, overflow: 'auto',
                  }}>
                    {msg.thinking}
                  </div>
                </details>
              )}
              <div style={{
                background: '#fff', color: '#374151',
                padding: '14px 18px', borderRadius: '18px 18px 18px 4px',
                fontSize: 14, lineHeight: 1.7,
                border: '1px solid #E5E7EB',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              }}>
                {formatMessage(msg.text)}
                {msg.provider && (
                  <div style={{ fontSize: 10, color: '#C4B5FD', marginTop: 8, textAlign: 'right' }}>
                    {msg.provider}
                  </div>
                )}
              </div>
            </div>
          )
        })}

        {/* Thinking in progress — expandable on click */}
        {chat.streaming && chat.currentThinking && chat.isThinking && (
          <ThinkingBubble thinking={chat.currentThinking} />
        )}

        {/* Streaming response */}
        {chat.streaming && chat.currentResponse && (
          <div style={{ alignSelf: 'flex-start', maxWidth: '85%' }}>
            <div style={{
              background: '#fff', color: '#374151',
              padding: '14px 18px', borderRadius: '18px 18px 18px 4px',
              fontSize: 14, lineHeight: 1.7,
              border: '1px solid #E5E7EB',
            }}>
              {formatMessage(chat.currentResponse)}
              <span style={{
                display: 'inline-block', width: 2, height: 16,
                background: '#6366F1', marginLeft: 2,
                animation: 'pulse 1s infinite',
                verticalAlign: 'text-bottom',
              }} />
            </div>
          </div>
        )}

        {/* Typing indicator */}
        {chat.streaming && !chat.currentResponse && !chat.currentThinking && (
          <div style={{ alignSelf: 'flex-start' }}>
            <div style={{
              background: '#fff', padding: '14px 20px',
              borderRadius: '18px 18px 18px 4px',
              border: '1px solid #E5E7EB',
              display: 'flex', gap: 5,
            }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: '#6366F1', opacity: 0.6,
                  animation: `pulse 1.4s ease-in-out ${i * 0.2}s infinite`,
                }} />
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      {showQuickActions && (
        <div style={{
          padding: '8px 20px 4px', display: 'flex', flexWrap: 'wrap', gap: 8,
          background: '#FAFBFC',
        }}>
          {QUICK_ACTIONS.map(action => (
            <button
              key={action.icon}
              onClick={() => handleSend(action.prompt[lang] || action.prompt.es)}
              style={{
                padding: '8px 14px', borderRadius: 20,
                border: '1px solid #E5E7EB', background: '#fff',
                fontSize: 13, cursor: 'pointer', color: '#374151',
                display: 'flex', alignItems: 'center', gap: 6,
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#6366F1'; e.currentTarget.style.background = '#EEF2FF' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.background = '#fff' }}
            >
              <span>{action.icon}</span>
              {lang === 'es' ? action.labelEs : action.labelEn}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} style={{
        padding: '12px 20px 16px', borderTop: '1px solid #E5E7EB',
        background: '#fff', display: 'flex', gap: 10,
      }}>
        <input
          ref={inputRef}
          type="text"
          value={chat.input}
          onChange={e => chat.setInput(e.target.value)}
          placeholder={lang === 'es' ? 'Describe lo que quieres automatizar...' : 'Describe what you want to automate...'}
          disabled={chat.streaming}
          style={{
            flex: 1, padding: '12px 16px', borderRadius: 14,
            border: '2px solid #E5E7EB', fontSize: 14,
            outline: 'none', transition: 'border-color 0.2s',
            color: '#111827', background: '#FAFBFC',
          }}
          onFocus={e => e.target.style.borderColor = '#6366F1'}
          onBlur={e => e.target.style.borderColor = '#E5E7EB'}
        />
        <button
          type="submit"
          disabled={chat.streaming || !chat.input.trim()}
          style={{
            width: 44, height: 44, borderRadius: 12, border: 'none',
            background: chat.input.trim() && !chat.streaming
              ? 'linear-gradient(135deg, #6366F1, #8B5CF6)' : '#E5E7EB',
            color: '#fff', fontSize: 18, cursor: chat.input.trim() ? 'pointer' : 'default',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.2s',
          }}
        >
          {'\u2191'}
        </button>
      </form>
    </div>
  )
}
