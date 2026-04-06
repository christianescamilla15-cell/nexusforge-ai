import { useRef, useEffect, useCallback } from 'react'
import useChatStream from './hooks/useChatStream'
import { usePreviewEvents, parseAssistantResponse } from './hooks/usePreviewEvents'

const QUICK_ACTIONS = [
  { icon: '\uD83C\uDFAB', labelEs: 'Clasificar tickets', labelEn: 'Classify tickets', prompt: { es: 'Quiero clasificar tickets de soporte automaticamente', en: 'I want to automatically classify support tickets' } },
  { icon: '\uD83D\uDCC4', labelEs: 'Analizar documentos', labelEn: 'Analyze documents', prompt: { es: 'Necesito analizar documentos y facturas automaticamente', en: 'I need to automatically analyze documents and invoices' } },
  { icon: '\uD83D\uDCE7', labelEs: 'Responder emails', labelEn: 'Reply to emails', prompt: { es: 'Quiero responder emails de clientes automaticamente', en: 'I want to automatically reply to customer emails' } },
  { icon: '\uD83D\uDCCA', labelEs: 'Generar reportes', labelEn: 'Generate reports', prompt: { es: 'Necesito generar reportes semanales automaticos', en: 'I need to generate automatic weekly reports' } },
  { icon: '\uD83D\uDCF1', labelEs: 'Monitorear redes', labelEn: 'Monitor social', prompt: { es: 'Quiero monitorear menciones de mi marca en redes sociales', en: 'I want to monitor brand mentions on social media' } },
  { icon: '\u2699\uFE0F', labelEs: 'Procesar datos', labelEn: 'Process data', prompt: { es: 'Necesito procesar y validar datos de multiples fuentes', en: 'I need to process and validate data from multiple sources' } },
]

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

  const handleSend = (text) => {
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
      background: '#FAFBFC',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid #E5E7EB',
        background: '#fff',
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

        {/* Thinking in progress */}
        {chat.streaming && chat.currentThinking && (
          <div style={{ alignSelf: 'flex-start', maxWidth: '90%', width: '100%' }}>
            <div style={{
              background: 'linear-gradient(135deg, #FEF3C7, #FDE68A)',
              color: '#78350F', padding: '14px 18px',
              borderRadius: '18px 18px 18px 4px',
              fontSize: 13, lineHeight: 1.6, fontStyle: 'italic',
              border: '2px solid #F59E0B',
              boxShadow: '0 2px 8px rgba(245,158,11,0.15)',
            }}>
              <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 8, color: '#B45309', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 16, animation: 'pulse 2s infinite' }}>{'\uD83E\uDDE0'}</span>
                {chat.isThinking
                  ? (lang === 'es' ? 'Pensando en tiempo real...' : 'Thinking in real-time...')
                  : (lang === 'es' ? 'Razonamiento completado' : 'Reasoning complete')}
              </div>
              <div style={{ maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {chat.currentThinking}
              </div>
            </div>
          </div>
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
