import { createContext, useContext, useState, useCallback } from 'react'

const PreviewEventContext = createContext(null)

/**
 * Preview event types:
 *   idle       — show default KPI dashboard
 *   workflow   — show workflow DAG visualization
 *   automation — show automation config preview
 *   building   — show building animation
 *   complete   — show completed automation summary
 */
export function PreviewEventProvider({ children }) {
  const [previewState, setPreviewState] = useState({ type: 'idle', data: null })

  const emitPreview = useCallback((event) => {
    setPreviewState(event)
  }, [])

  const resetPreview = useCallback(() => {
    setPreviewState({ type: 'idle', data: null })
  }, [])

  return (
    <PreviewEventContext.Provider value={{ previewState, emitPreview, resetPreview }}>
      {children}
    </PreviewEventContext.Provider>
  )
}

export function usePreviewEvents() {
  const ctx = useContext(PreviewEventContext)
  if (!ctx) return { previewState: { type: 'idle', data: null }, emitPreview: () => {}, resetPreview: () => {} }
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
