export function connectExecutionWS(runId, onMessage) {
  const wsUrl = `${(import.meta.env.VITE_WS_URL || 'ws://localhost:8000')}/api/executions/ws/${runId}`
  const ws = new WebSocket(wsUrl)
  ws.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data))
    } catch (err) {
      console.error('WS JSON parse error:', err)
    }
  }
  ws.onerror = (err) => console.error('WS error:', err)
  return ws
}
