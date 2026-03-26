export function connectExecutionWS(runId, onMessage) {
  const wsUrl = `${(import.meta.env.VITE_WS_URL || 'ws://localhost:8000')}/api/executions/ws/${runId}`
  const ws = new WebSocket(wsUrl)
  ws.onmessage = (event) => onMessage(JSON.parse(event.data))
  ws.onerror = (err) => console.error('WS error:', err)
  return ws
}
