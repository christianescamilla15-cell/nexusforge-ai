import { useState, useRef, useCallback } from 'react'
import { getApiUrl } from '../../../services/api'

/**
 * Extracted chat streaming logic — reusable by ChatPanel and ChatAssistant.
 * Handles SSE streaming with thinking/text/done event types.
 */
export default function useChatStream(lang = 'es') {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [currentResponse, setCurrentResponse] = useState('')
  const [currentThinking, setCurrentThinking] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [provider, setProvider] = useState('')
  const abortRef = useRef(null)

  const sendMessage = useCallback(async (text, onChunk) => {
    if (!text.trim() || streaming) return

    const userMsg = { id: `u-${Date.now()}`, role: 'user', text: text.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setStreaming(true)
    setCurrentResponse('')
    setCurrentThinking('')
    setIsThinking(false)

    const history = [...messages, userMsg]
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({ role: m.role, content: m.text }))

    const apiUrl = getApiUrl()
    const token = typeof window !== 'undefined' ? localStorage.getItem('nf_token') : null
    const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}

    try {
      abortRef.current = new AbortController()

      const response = await fetch(`${apiUrl}/wizard/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ messages: history, language: lang }),
        signal: abortRef.current.signal,
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullText = ''
      let thinkText = ''
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data: ')) continue
          try {
            const data = JSON.parse(trimmed.slice(6))
            if (data.type === 'thinking') {
              thinkText += data.content
              setCurrentThinking(thinkText)
              setIsThinking(true)
            }
            if (data.type === 'thinking_done') {
              setIsThinking(false)
            }
            if (data.type === 'text') {
              fullText += data.content
              setCurrentResponse(fullText)
              if (onChunk) onChunk(fullText)
            }
            if (data.type === 'done') {
              const msg = {
                id: `a-${Date.now()}`,
                role: 'assistant',
                text: fullText,
                thinking: thinkText || null,
                provider: data.provider || '',
              }
              setMessages(prev => [...prev, msg])
              setProvider(data.provider || '')
              setCurrentResponse('')
              setCurrentThinking('')
              setIsThinking(false)
              setStreaming(false)
            }
          } catch {
            // skip malformed chunks
          }
        }
      }

      // Fallback finalize if no 'done' event
      if (fullText && streaming) {
        setMessages(prev => [...prev, {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: fullText,
          thinking: thinkText || null,
        }])
        setCurrentResponse('')
        setCurrentThinking('')
        setIsThinking(false)
        setStreaming(false)
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      setMessages(prev => [...prev, {
        id: `e-${Date.now()}`,
        role: 'assistant',
        text: lang === 'es'
          ? 'Error de conexion. Verifica que el backend este activo.'
          : 'Connection error. Check the backend is running.',
      }])
      setCurrentResponse('')
      setCurrentThinking('')
      setIsThinking(false)
      setStreaming(false)
    }
  }, [lang, messages, streaming])

  const abort = useCallback(() => {
    if (abortRef.current) abortRef.current.abort()
  }, [])

  return {
    messages, setMessages,
    input, setInput,
    streaming,
    currentResponse, currentThinking, isThinking,
    provider,
    sendMessage, abort,
  }
}
