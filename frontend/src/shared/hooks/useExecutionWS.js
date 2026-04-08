import { useEffect, useRef, useState, useCallback } from 'react'
import { getApiUrl } from '../../services/api'

/**
 * Hook that connects to the execution WebSocket for live step-by-step updates.
 * Falls back to polling if WS is unavailable (e.g., Render free tier).
 *
 * Events from backend:
 *   run_started    — { event, groups }
 *   group_started  — { event, group, steps: [...] }
 *   step_completed — { event, step, duration_ms, tokens }
 *   step_failed    — { event, step, duration_ms, tokens }
 *   run_completed  — { event, total_tokens, total_cost_usd }
 *   run_failed     — { event, failed_step }
 */
export function useExecutionWS(runId, isActive) {
  const [stepStatuses, setStepStatuses] = useState({})
  const [liveEvents, setLiveEvents] = useState([])
  const [runStatus, setRunStatus] = useState(null) // null = no update yet
  const wsRef = useRef(null)

  const addEvent = useCallback((evt) => {
    setLiveEvents(prev => [...prev, { ...evt, timestamp: new Date().toISOString() }])
  }, [])

  useEffect(() => {
    if (!runId || !isActive) return

    const apiUrl = getApiUrl()
    if (!apiUrl) return

    const wsUrl = apiUrl.replace(/^http/, 'ws').replace(/\/api$/, '/api/executions') + `/ws/${runId}`
    let ws

    try {
      ws = new WebSocket(wsUrl)
    } catch {
      return // WS not supported or URL invalid
    }

    ws.onopen = () => {
      addEvent({ event_type: 'info', detail: 'Connected to live execution stream' })
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        const event = msg.event

        if (event === 'run_started') {
          addEvent({ event_type: 'info', detail: `Run started — ${msg.groups} group(s)` })
        } else if (event === 'group_started') {
          const steps = msg.steps || []
          steps.forEach(s => setStepStatuses(prev => ({ ...prev, [s]: 'running' })))
          addEvent({ event_type: 'step_started', step_name: steps.join(', '), detail: `Group ${msg.group} started` })
        } else if (event === 'step_completed') {
          setStepStatuses(prev => ({ ...prev, [msg.step]: 'completed' }))
          addEvent({
            event_type: 'step_completed', step_name: msg.step,
            detail: `${msg.tokens?.toLocaleString() || 0} tokens, ${msg.duration_ms || 0}ms`,
          })
        } else if (event === 'step_failed') {
          setStepStatuses(prev => ({ ...prev, [msg.step]: 'failed' }))
          addEvent({ event_type: 'step_failed', step_name: msg.step, detail: 'Step failed' })
        } else if (event === 'run_completed') {
          setRunStatus('completed')
          addEvent({
            event_type: 'step_completed', step_name: '',
            detail: `Run completed — ${msg.total_tokens} tokens, $${Number(msg.total_cost_usd || 0).toFixed(3)}`,
          })
        } else if (event === 'run_failed') {
          setRunStatus('failed')
          addEvent({ event_type: 'step_failed', step_name: msg.failed_step || '', detail: 'Run failed' })
        }
      } catch { /* ignore malformed */ }
    }

    ws.onerror = () => {
      // WS failed — polling fallback is already in place
    }

    ws.onclose = () => {
      wsRef.current = null
    }

    wsRef.current = ws

    // Ping keepalive every 25s
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping')
    }, 25000)

    return () => {
      clearInterval(pingInterval)
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close()
      }
    }
  }, [runId, isActive, addEvent])

  return { stepStatuses, liveEvents, runStatus }
}
