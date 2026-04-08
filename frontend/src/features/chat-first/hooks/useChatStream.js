import { useState, useRef, useCallback, useEffect } from 'react'
import { getApiUrl } from '../../../services/api'

const STORAGE_KEY = 'nxf_chat_history'

function loadMessages() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

function saveMessages(msgs) {
  try {
    // Keep last 50 messages to avoid storage overflow
    const toSave = msgs.filter(m => m.role !== 'system').slice(-50)
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
  } catch { /* storage full */ }
}

/**
 * Extracted chat streaming logic — reusable by ChatPanel and ChatAssistant.
 * Handles SSE streaming with thinking/text/done event types.
 * Persists messages in sessionStorage.
 */
export default function useChatStream(lang = 'es') {
  const [messages, setMessages] = useState(() => loadMessages())
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [currentResponse, setCurrentResponse] = useState('')
  const [currentThinking, setCurrentThinking] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [provider, setProvider] = useState('')
  const abortRef = useRef(null)

  // Persist messages to sessionStorage
  useEffect(() => {
    if (messages.length > 0) saveMessages(messages)
  }, [messages])

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

    let retried = false
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

      // Retry once on transient network errors
      if (!retried) {
        retried = true
        try {
          await new Promise(r => setTimeout(r, 1500))
          // Re-attempt the same request
          abortRef.current = new AbortController()
          const retryRes = await fetch(`${apiUrl}/wizard/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders },
            body: JSON.stringify({ messages: history, language: lang }),
            signal: abortRef.current.signal,
          })
          if (retryRes.ok) {
            const reader2 = retryRes.body.getReader()
            const decoder2 = new TextDecoder()
            let buf2 = ''
            while (true) {
              const { done: d2, value: v2 } = await reader2.read()
              if (d2) break
              buf2 += decoder2.decode(v2, { stream: true })
              const lines2 = buf2.split('\n')
              buf2 = lines2.pop() || ''
              for (const line of lines2) {
                const tr = line.trim()
                if (!tr.startsWith('data: ')) continue
                try {
                  const data = JSON.parse(tr.slice(6))
                  if (data.type === 'text') { fullText += data.content; setCurrentResponse(fullText); if (onChunk) onChunk(fullText) }
                  if (data.type === 'done') {
                    setMessages(prev => [...prev, { id: `a-${Date.now()}`, role: 'assistant', text: fullText, thinking: thinkText || null, provider: data.provider || '' }])
                    setProvider(data.provider || '')
                  }
                } catch {}
              }
            }
            if (fullText) {
              setMessages(prev => {
                if (prev.some(m => m.text === fullText)) return prev
                return [...prev, { id: `a-${Date.now()}`, role: 'assistant', text: fullText }]
              })
            }
            setCurrentResponse(''); setCurrentThinking(''); setIsThinking(false); setStreaming(false)
            return
          }
        } catch { /* retry also failed */ }
      }

      setMessages(prev => [...prev, {
        id: `e-${Date.now()}`,
        role: 'assistant',
        text: lang === 'es'
          ? 'Error de conexion. Verifica que el backend este activo en Configuracion.'
          : 'Connection error. Check the backend is running in Settings.',
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
