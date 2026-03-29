import { useState, useRef, useEffect, useCallback } from 'react'
import { generateResponse } from './chatEngine'

const QUICK_ACTIONS = [
  { label: 'What is NexusForge?', labelEs: '¿Qué es NexusForge?' },
  { label: 'How does it work?', labelEs: '¿Cómo funciona?' },
  { label: 'Agents', labelEs: 'Agentes' },
  { label: 'Topologies', labelEs: 'Topologías' },
  { label: 'Self-Healing', labelEs: 'Auto-Reparación' },
  { label: 'What real use cases does NexusForge have?', labelEs: '¿Qué casos de uso reales tiene NexusForge?' },
  { label: 'Explain the Operations Assistant', labelEs: 'Explica el Asistente de Operaciones' },
  { label: 'How does Document Intelligence work?', labelEs: '¿Cómo funciona la Inteligencia Documental?' },
  { label: 'What is the Portfolio Copilot?', labelEs: '¿Qué es el Copiloto de Portafolio?' },
  { label: 'How does the Playground work?', labelEs: '¿Cómo funciona el Playground?' },
  { label: 'What cost metrics are tracked?', labelEs: '¿Qué métricas de costos se rastrean?' },
  { label: 'RAG Pipeline', labelEs: 'Pipeline RAG' },
  { label: 'Architecture', labelEs: 'Arquitectura' },
  { label: 'Help', labelEs: 'Ayuda completa' },
]

function formatMessage(text) {
  if (!text) return null
  const lines = text.split('\n')
  const elements = []

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i]

    const parts = []
    let remaining = line
    let keyIdx = 0
    while (remaining.length > 0) {
      const boldStart = remaining.indexOf('**')
      if (boldStart === -1) {
        parts.push(remaining)
        break
      }
      const boldEnd = remaining.indexOf('**', boldStart + 2)
      if (boldEnd === -1) {
        parts.push(remaining)
        break
      }
      if (boldStart > 0) {
        parts.push(remaining.slice(0, boldStart))
      }
      parts.push(
        <strong key={`b-${i}-${keyIdx++}`} style={{ color: '#111827', fontWeight: 600 }}>
          {remaining.slice(boldStart + 2, boldEnd)}
        </strong>
      )
      remaining = remaining.slice(boldEnd + 2)
    }

    const processed = []
    for (const part of parts) {
      if (typeof part !== 'string') {
        processed.push(part)
        continue
      }
      let rest = part
      while (rest.length > 0) {
        const codeStart = rest.indexOf('`')
        if (codeStart === -1) {
          processed.push(rest)
          break
        }
        const codeEnd = rest.indexOf('`', codeStart + 1)
        if (codeEnd === -1) {
          processed.push(rest)
          break
        }
        if (codeStart > 0) processed.push(rest.slice(0, codeStart))
        processed.push(
          <code key={`c-${i}-${keyIdx++}`} style={{
            background: 'rgba(37,99,235,0.06)', padding: '1px 5px',
            borderRadius: 3, fontSize: 13, fontFamily: 'monospace', color: '#2563EB',
          }}>
            {rest.slice(codeStart + 1, codeEnd)}
          </code>
        )
        rest = rest.slice(codeEnd + 1)
      }
    }

    if (line.trim() === '') {
      elements.push(<br key={`br-${i}`} />)
    } else {
      elements.push(
        <div key={`line-${i}`} style={{
          marginBottom: line.match(/^(\d+\.|-)/) ? 4 : 2,
          paddingLeft: line.match(/^(\d+\.|-)/) ? 8 : 0,
        }}>
          {processed}
        </div>
      )
    }
  }

  return elements
}

function TypingIndicator() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 4, padding: '12px 16px',
    }}>
      {[0, 1, 2].map((i) => (
        <div key={i} style={{
          width: 7, height: 7, borderRadius: '50%', background: '#2563EB',
          animation: `chatTypingBounce 1.2s ease-in-out ${i * 0.2}s infinite`,
        }} />
      ))}
    </div>
  )
}

export default function ChatAssistant({ lang = 'en' }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [typing, setTyping] = useState(false)
  const [hasUnread, setHasUnread] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, typing, scrollToBottom])

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus()
    }
  }, [open])

  useEffect(() => {
    if (open && messages.length === 0) {
      setMessages([{
        id: 'welcome',
        role: 'system',
        text: lang === 'es'
          ? 'Bienvenido al asistente de NexusForge AI'
          : 'Welcome to the NexusForge AI assistant',
      }])
    }
  }, [open, messages.length, lang])

  const sendMessage = useCallback((text) => {
    if (!text.trim()) return

    const userMsg = { id: `u-${Date.now()}`, role: 'user', text: text.trim() }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setTyping(true)

    setTimeout(() => {
      const response = generateResponse(text, lang)
      const assistantMsg = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        text: response.text,
        topic: response.topic,
        confidence: response.confidence,
        sources: response.sources,
        suggestedFollowups: response.suggestedFollowups,
      }
      setMessages((prev) => [...prev, assistantMsg])
      setTyping(false)

      if (!open) {
        setHasUnread(true)
      }
    }, 300 + Math.random() * 400)
  }, [lang, open])

  const handleSubmit = (e) => {
    e.preventDefault()
    sendMessage(input)
  }

  const handleChipClick = (text) => {
    sendMessage(text)
  }

  const toggleOpen = () => {
    setOpen((prev) => !prev)
    if (!open) setHasUnread(false)
  }

  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant')
  const followups = lastAssistant?.suggestedFollowups || []
  const showQuickActions = messages.length <= 1

  return (
    <>
      <style>{`
        @keyframes chatTypingBounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30% { transform: translateY(-6px); opacity: 1; }
        }
        @keyframes chatPulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(37,99,235,0.4); }
          50% { box-shadow: 0 0 0 10px rgba(37,99,235,0); }
        }
        @keyframes chatSlideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes chatFadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @media (max-width: 768px) {
          .nf-chat-panel {
            width: calc(100vw - 32px) !important;
            max-height: 60vh !important;
            height: 60vh !important;
            bottom: 80px !important;
            right: 16px !important;
            left: 16px !important;
            border-radius: 16px 16px 12px 12px !important;
          }
          .nf-chat-fab {
            bottom: 80px !important;
            right: 16px !important;
            width: 52px !important;
            height: 52px !important;
          }
          .nf-chat-panel .nf-chat-chips {
            max-height: 80px;
            overflow-y: auto;
          }
        }
      `}</style>

      {/* Floating button */}
      {!open && (
        <button
          className="nf-chat-fab"
          data-tour="chat-button"
          onClick={toggleOpen}
          aria-label="AI Assistant"
          title="AI Assistant"
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            width: 60,
            height: 60,
            borderRadius: '50%',
            background: '#2563EB',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            animation: 'chatPulse 2.5s ease-in-out infinite',
            transition: 'transform 0.2s ease',
            boxShadow: '0 4px 20px rgba(37,99,235,0.3)',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.08)' }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)' }}
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
          </svg>

          {hasUnread && (
            <span style={{
              position: 'absolute', top: -2, right: -2,
              width: 18, height: 18, borderRadius: '50%',
              background: '#DC2626', color: '#fff',
              fontSize: 11, fontWeight: 700,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: '2px solid #FFFFFF',
            }}>
              1
            </span>
          )}
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div
          className="nf-chat-panel"
          role="dialog"
          aria-label="NexusForge Assistant"
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            width: 400,
            height: 600,
            background: '#FFFFFF',
            borderRadius: 16,
            border: '1px solid #E5E7EB',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            zIndex: 1000,
            animation: 'chatSlideUp 0.3s ease-out',
            boxShadow: '0 12px 48px rgba(0,0,0,0.12), 0 0 0 1px rgba(37,99,235,0.05)',
          }}
        >
          {/* Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '14px 16px',
            borderBottom: '1px solid #E5E7EB',
            background: '#FAFBFC',
            flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: '#2563EB',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14, color: '#111827' }}>
                  NexusForge Assistant
                </div>
                <div style={{ fontSize: 11, color: '#9CA3AF' }}>
                  {lang === 'es' ? 'Siempre disponible' : 'Always available'}
                </div>
              </div>
            </div>
            <button
              onClick={toggleOpen}
              aria-label={lang === 'es' ? 'Minimizar chat' : 'Minimize chat'}
              style={{
                background: 'none', border: 'none', color: '#9CA3AF',
                cursor: 'pointer', padding: 4, borderRadius: 6,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'color 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = '#111827' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = '#9CA3AF' }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div style={{
            flex: 1, overflowY: 'auto', padding: '12px 12px 4px',
            display: 'flex', flexDirection: 'column', gap: 8,
            background: '#F9FAFB',
          }}>
            {messages.map((msg) => {
              if (msg.role === 'system') {
                return (
                  <div key={msg.id} style={{
                    textAlign: 'center', fontSize: 12, color: '#9CA3AF',
                    padding: '8px 0', animation: 'chatFadeIn 0.3s ease',
                  }}>
                    {msg.text}
                  </div>
                )
              }

              if (msg.role === 'user') {
                return (
                  <div key={msg.id} style={{
                    alignSelf: 'flex-end', maxWidth: '85%',
                    animation: 'chatFadeIn 0.2s ease',
                  }}>
                    <div style={{
                      background: '#2563EB', color: '#fff',
                      padding: '10px 14px', borderRadius: '14px 14px 4px 14px',
                      fontSize: 14, lineHeight: 1.5,
                    }}>
                      {msg.text}
                    </div>
                  </div>
                )
              }

              return (
                <div key={msg.id} style={{
                  alignSelf: 'flex-start', maxWidth: '90%',
                  animation: 'chatFadeIn 0.3s ease',
                }}>
                  <div style={{
                    background: '#FFFFFF', color: '#374151',
                    padding: '12px 14px', borderRadius: '14px 14px 14px 4px',
                    fontSize: 14, lineHeight: 1.6,
                    border: '1px solid #E5E7EB',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                  }}>
                    {formatMessage(msg.text)}
                  </div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{
                      fontSize: 11, color: '#9CA3AF', marginTop: 4, paddingLeft: 4,
                    }}>
                      Fuente: {msg.sources.join(', ')}
                    </div>
                  )}
                </div>
              )
            })}

            {typing && (
              <div style={{
                alignSelf: 'flex-start',
                background: '#FFFFFF',
                borderRadius: '14px 14px 14px 4px',
                border: '1px solid #E5E7EB',
              }}>
                <TypingIndicator />
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Suggested followups */}
          {!typing && followups.length > 0 && !showQuickActions && (
            <div className="nf-chat-chips" style={{
              padding: '4px 12px 4px', display: 'flex', flexWrap: 'wrap', gap: 6,
              background: '#FFFFFF',
            }}>
              {followups.map((f) => (
                <button
                  key={f}
                  onClick={() => handleChipClick(f)}
                  aria-label={f}
                  style={{
                    padding: '5px 10px', borderRadius: 12,
                    border: '1px solid rgba(37,99,235,0.2)',
                    background: 'rgba(37,99,235,0.04)',
                    color: '#2563EB', fontSize: 12,
                    cursor: 'pointer', transition: 'all 0.15s',
                    whiteSpace: 'nowrap',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(37,99,235,0.08)'
                    e.currentTarget.style.borderColor = 'rgba(37,99,235,0.35)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(37,99,235,0.04)'
                    e.currentTarget.style.borderColor = 'rgba(37,99,235,0.2)'
                  }}
                >
                  {f}
                </button>
              ))}
            </div>
          )}

          {/* Quick action chips */}
          {showQuickActions && !typing && (
            <div className="nf-chat-chips" style={{
              padding: '4px 12px 4px', display: 'flex', flexWrap: 'wrap', gap: 6,
              background: '#FFFFFF',
            }}>
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.label}
                  onClick={() => handleChipClick(lang === 'es' ? action.labelEs : action.label)}
                  aria-label={lang === 'es' ? action.labelEs : action.label}
                  style={{
                    padding: '5px 10px', borderRadius: 12,
                    border: '1px solid rgba(37,99,235,0.2)',
                    background: 'rgba(37,99,235,0.04)',
                    color: '#2563EB', fontSize: 12,
                    cursor: 'pointer', transition: 'all 0.15s',
                    whiteSpace: 'nowrap',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(37,99,235,0.08)'
                    e.currentTarget.style.borderColor = 'rgba(37,99,235,0.35)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(37,99,235,0.04)'
                    e.currentTarget.style.borderColor = 'rgba(37,99,235,0.2)'
                  }}
                >
                  {lang === 'es' ? action.labelEs : action.label}
                </button>
              ))}
            </div>
          )}

          {/* Input area */}
          <form
            onSubmit={handleSubmit}
            style={{
              padding: '10px 12px 12px',
              borderTop: '1px solid #E5E7EB',
              display: 'flex', gap: 8, flexShrink: 0,
              background: '#FFFFFF',
            }}
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={lang === 'es' ? 'Pregúntame sobre NexusForge...' : 'Ask about NexusForge...'}
              aria-label={lang === 'es' ? 'Escribir mensaje' : 'Type a message'}
              disabled={typing}
              style={{
                flex: 1, padding: '10px 14px', borderRadius: 10,
                border: '1px solid #E5E7EB',
                background: '#F9FAFB',
                color: '#111827', fontSize: 14, outline: 'none',
                transition: 'border-color 0.15s',
              }}
              onFocus={(e) => { e.target.style.borderColor = '#2563EB' }}
              onBlur={(e) => { e.target.style.borderColor = '#E5E7EB' }}
            />
            <button
              type="submit"
              disabled={!input.trim() || typing}
              aria-label={lang === 'es' ? 'Enviar mensaje' : 'Send message'}
              style={{
                width: 40, height: 40, borderRadius: 10,
                border: 'none',
                background: input.trim() && !typing
                  ? '#2563EB'
                  : '#F3F4F6',
                color: input.trim() && !typing ? '#fff' : '#9CA3AF',
                cursor: input.trim() && !typing ? 'pointer' : 'default',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.15s', flexShrink: 0,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
        </div>
      )}
    </>
  )
}
