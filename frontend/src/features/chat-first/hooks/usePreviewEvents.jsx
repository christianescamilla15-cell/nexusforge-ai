import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { getApiUrl } from '../../../services/api'

const PreviewEventContext = createContext(null)

/**
 * Preview event types:
 *   idle       — show default KPI dashboard
 *   workflow   — show workflow DAG with live step statuses via WebSocket
 *   building   — show building animation
 *   complete   — show completed automation summary
 *   step       — show conversation step progress
 */
export function PreviewEventProvider({ children }) {
  const [previewState, setPreviewState] = useState({ type: 'idle', data: null })
  // stepStatuses: { [stepName]: 'pending' | 'running' | 'completed' | 'failed' }
  const [stepStatuses, setStepStatuses] = useState({})
  const wsRef = useRef(null)

  const emitPreview = useCallback((event) => {
    setPreviewState(event)
    // When a workflow run starts, open WebSocket for live step updates
    if (event.type === 'workflow' && event.data?.runId) {
      if (wsRef.current) wsRef.current.close()
      setStepStatuses({})
      // Backend mounts the WS handler at /api/executions/ws/{runId} —
      // mirror the URL builder from useExecutionWS.js so chat-first
      // preview actually receives step events.
      const wsBase = getApiUrl().replace(/^http/, 'ws').replace(/\/api$/, '/api/executions')
      const ws = new WebSocket(`${wsBase}/ws/${event.data.runId}`)
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          // Backend publishes: { step_name, status } or { type: 'step_update', step_name, status }
          const stepName = msg.step_name || msg.name
          const status = msg.status
          if (stepName && status) {
            setStepStatuses(prev => ({ ...prev, [stepName]: status }))
          }
        } catch { /* ignore malformed */ }
      }
      ws.onerror = () => {}
      wsRef.current = ws
    }
  }, [])

  const resetPreview = useCallback(() => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null }
    setPreviewState({ type: 'idle', data: null })
    setStepStatuses({})
  }, [])

  // Cleanup on unmount
  useEffect(() => () => { if (wsRef.current) wsRef.current.close() }, [])

  return (
    <PreviewEventContext.Provider value={{ previewState, stepStatuses, emitPreview, resetPreview }}>
      {children}
    </PreviewEventContext.Provider>
  )
}

export function usePreviewEvents() {
  const ctx = useContext(PreviewEventContext)
  if (!ctx) return { previewState: { type: 'idle', data: null }, stepStatuses: {}, emitPreview: () => {}, resetPreview: () => {} }
  return ctx
}

/**
 * Parse assistant response text to detect structured content for preview.
 * Conservative — only emits when high confidence patterns match.
 */
export function parseAssistantResponse(text, lang = 'es') {
  if (!text || text.length < 20) return null

  const lower = text.toLowerCase()

  // Detect workflow/automation being built
  const buildingWords = ['creando', 'creating', 'configurando', 'configuring', 'construyendo', 'building', 'publicando', 'publishing']
  if (buildingWords.some(w => lower.includes(w))) {
    return { type: 'building', data: { text } }
  }

  // Detect automation complete
  const completeWords = ['listo', 'ready', 'publicada', 'published', 'creada', 'created', 'completada', 'completed']
  const nameMatch = text.match(/[""]([^""]+)[""]/)
  if (completeWords.some(w => lower.includes(w)) && nameMatch) {
    return {
      type: 'complete',
      data: {
        name: nameMatch[1],
        text: text.slice(0, 200),
      },
    }
  }

  // Detect step progression (questions about data source, processing, output)
  const stepPatterns = [
    { pattern: /d[oó]nde llegan|where.*come|data source|fuente/i, step: 'source' },
    { pattern: /qu[eé] necesitas|what.*do.*with|procesar|clasificar/i, step: 'processing' },
    { pattern: /d[oó]nde.*result|where.*send|email.*slack.*notion/i, step: 'output' },
    { pattern: /c[oó]mo.*llam|what.*name|color|nombre/i, step: 'customize' },
  ]

  for (const { pattern, step } of stepPatterns) {
    if (pattern.test(text)) {
      return { type: 'step', data: { step, text: text.slice(0, 150) } }
    }
  }

  return null
}
