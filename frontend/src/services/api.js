// ---------------------------------------------------------------------------
// NexusForge API Service — dual-mode: real backend or demo data.
// Mode is controlled via localStorage ('demo' or 'real').
// STRICT: Real mode NEVER falls back to demo data.
// ---------------------------------------------------------------------------

// ── Mode helpers ────────────────────────────────────────────────────────────

/** Return the current mode: 'demo' or 'real'.
 *  If mode is 'real' but no API URL exists, auto-revert to 'demo'. */
export function getMode() {
  if (typeof window === 'undefined') return 'demo'
  const saved = localStorage.getItem('nexusforge_mode') || 'demo'
  // Safety: if real mode but no URL configured, revert to demo
  if (saved === 'real') {
    const url = localStorage.getItem('nexusforge_api_url') || import.meta.env.VITE_API_URL || ''
    if (!url) {
      localStorage.setItem('nexusforge_mode', 'demo')
      return 'demo'
    }
  }
  return saved
}

/** Persist mode to localStorage and notify listeners. */
export function setMode(mode) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('nexusforge_mode', mode)
    window.dispatchEvent(new Event('nexusforge-mode-change'))
  }
}

/** Return the user-configured API URL (only relevant in real mode). Empty string = not configured. */
export function getApiUrl() {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem('nexusforge_api_url')
    || import.meta.env.VITE_API_URL
    || 'https://nexusforge-two.vercel.app/api'
}

/** Return the source of the current API URL for diagnostics. */
export function getApiUrlSource() {
  if (typeof window === 'undefined') return 'none'
  if (localStorage.getItem('nexusforge_api_url')) return 'localStorage'
  if (import.meta.env.VITE_API_URL) return 'env'
  return 'none'
}

/** Persist API URL to localStorage. */
export function setApiUrl(url) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('nexusforge_api_url', url)
  }
}

// ── Health check ────────────────────────────────────────────────────────────

/** Check if the configured backend is reachable. */
export async function checkBackendHealth() {
  const apiUrl = getApiUrl()
  if (!apiUrl) return { status: 'no_url', message: 'No API URL configured' }

  try {
    const response = await fetch(`${apiUrl}/health`, { signal: AbortSignal.timeout(3000) })
    if (response.ok) return { status: 'connected', message: 'Backend is reachable' }
    return { status: 'error', message: `HTTP ${response.status}` }
  } catch (e) {
    return { status: 'unreachable', message: e.message }
  }
}

// ── Public helpers ──────────────────────────────────────────────────────────

let _isDemoMode = true

/** True when the last request(s) used demo data. */
export function isDemoMode() {
  return _isDemoMode
}

/**
 * Generic fetcher — STRICT mode behavior.
 * - Demo mode: returns demo data immediately (no network request).
 * - Real mode: calls backend. On failure returns { data: null, error: "..." }.
 *   NEVER falls back to demo data.
 */
export async function fetchAPI(endpoint, options = {}) {
  const mode = getMode()

  // DEMO MODE: always return demo data, never call backend
  if (mode === 'demo') {
    _isDemoMode = true
    return { data: getDemoData(endpoint, options), isDemo: true, error: null }
  }

  // REAL MODE: call backend, NEVER fall back to demo
  const apiUrl = getApiUrl()
  if (!apiUrl) {
    _isDemoMode = false
    return {
      data: null, isDemo: false,
      error: 'No API URL configured. Go to Settings to set the backend URL.',
    }
  }

  try {
    const res = await fetch(`${apiUrl}${endpoint}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
      signal: AbortSignal.timeout(10000),
    })

    if (!res.ok) {
      _isDemoMode = false
      return { data: null, isDemo: false, error: `Backend error: HTTP ${res.status}` }
    }

    _isDemoMode = false
    return { data: await res.json(), isDemo: false, error: null }
  } catch (err) {
    // STRICT: do NOT return demo data. Return error.
    _isDemoMode = false
    return {
      data: null, isDemo: false,
      error: `Backend unreachable: ${err.message}. Check Settings or switch to Demo mode.`,
    }
  }
}

/** Convenience wrappers matching the old `api` shape. */
export const api = {
  get: (path) => fetchAPI(path),
  post: (path, data) =>
    fetchAPI(path, { method: 'POST', body: JSON.stringify(data) }),
  put: (path, data) =>
    fetchAPI(path, { method: 'PUT', body: JSON.stringify(data) }),
  del: (path) => fetchAPI(path, { method: 'DELETE' }),
}

// ── Demo data router ────────────────────────────────────────────────────────

function getDemoData(endpoint) {
  if (endpoint.includes('/reliability/health')) return DEMO_HEALTH
  if (endpoint.includes('/runs'))              return DEMO_RUNS_RESPONSE
  if (endpoint.includes('/enterprise-ops'))    return DEMO_ENTERPRISE_RESULT
  if (endpoint.includes('/document-intelligence')) return DEMO_DOC_RESULT
  if (endpoint.includes('/portfolio-copilot')) return DEMO_COPILOT_RESULT
  return {}
}

// ── Demo datasets ───────────────────────────────────────────────────────────

const DEMO_RUNS = [
  {
    id: 'run-demo-001',
    workflow_name: 'Enterprise Ops Pipeline',
    status: 'completed',
    started_at: new Date(Date.now() - 3600000).toISOString(),
    finished_at: new Date(Date.now() - 3540000).toISOString(),
    latency_ms: 1240,
    agents_used: ['IntakeAgent', 'IntentClassifierAgent', 'CRMUpdateAgent', 'SupervisorAgent'],
  },
  {
    id: 'run-demo-002',
    workflow_name: 'Document Intelligence',
    status: 'completed',
    started_at: new Date(Date.now() - 7200000).toISOString(),
    finished_at: new Date(Date.now() - 7140000).toISOString(),
    latency_ms: 890,
    agents_used: ['DocumentRAGAgent', 'SummarizerAgent'],
  },
  {
    id: 'run-demo-003',
    workflow_name: 'Portfolio Copilot',
    status: 'completed',
    started_at: new Date(Date.now() - 10800000).toISOString(),
    finished_at: new Date(Date.now() - 10740000).toISOString(),
    latency_ms: 2100,
    agents_used: ['PortfolioAnalyzer', 'RiskAgent', 'RecommenderAgent'],
  },
  {
    id: 'run-demo-004',
    workflow_name: 'Enterprise Ops Pipeline',
    status: 'failed',
    started_at: new Date(Date.now() - 14400000).toISOString(),
    finished_at: new Date(Date.now() - 14380000).toISOString(),
    latency_ms: 4500,
    agents_used: ['IntakeAgent', 'IntentClassifierAgent'],
    error: 'Timeout waiting for CRM response',
  },
  {
    id: 'run-demo-005',
    workflow_name: 'Document Intelligence',
    status: 'completed',
    started_at: new Date(Date.now() - 18000000).toISOString(),
    finished_at: new Date(Date.now() - 17940000).toISOString(),
    latency_ms: 750,
    agents_used: ['DocumentRAGAgent', 'SummarizerAgent', 'TranslatorAgent'],
  },
]

const DEMO_RUNS_RESPONSE = {
  runs: DEMO_RUNS,
  total: DEMO_RUNS.length,
}

const DEMO_HEALTH = {
  status: 'healthy',
  total_runs: 47,
  failed_runs: 3,
  system_success_rate: 0.936,
  total_agents_tracked: 12,
  avg_latency_ms: 1380,
  agents: [
    { agent: 'IntakeAgent',           executions: 47 },
    { agent: 'IntentClassifierAgent', executions: 47 },
    { agent: 'DocumentRAGAgent',      executions: 32 },
    { agent: 'CRMUpdateAgent',        executions: 28 },
    { agent: 'SupervisorAgent',       executions: 47 },
    { agent: 'SchedulerAgent',        executions: 15 },
    { agent: 'NotificationAgent',     executions: 22 },
  ],
}

export const DEMO_ENTERPRISE_RESULT = {
  status: 'completed',
  intent: 'reschedule_meeting',
  customer_name: 'Carlos Rivera',
  response_message:
    'Your Friday meeting has been rescheduled to Monday at 10:00 AM. ' +
    'A calendar invitation has been sent to all participants.\n\n' +
    'Su reunion del viernes ha sido reprogramada al lunes a las 10:00 AM. ' +
    'Se envio una invitacion de calendario a todos los participantes.',
  actions_taken: [
    'Intent classified: reschedule_meeting',
    'Customer context loaded: Carlos Rivera (CUST-001)',
    'Calendar lookup: Friday 3:00 PM meeting found',
    'Meeting rescheduled to Monday 10:00 AM',
    'CRM interaction logged',
    'Internal notification dispatched',
  ],
  documents_consulted: ['scheduling-policy.md', 'customer-sla-terms.md'],
  crm_updated: true,
  notification_sent: true,
  processing_time_ms: 1240,
  agents_used: [
    'IntakeAgent',
    'IntentClassifierAgent',
    'CustomerContextAgent',
    'DocumentRAGAgent',
    'SchedulerAgent',
    'CRMUpdateAgent',
    'NotificationAgent',
    'SupervisorAgent',
  ],
}

export const DEMO_DOC_RESULT = {
  status: 'completed',
  summary:
    'The document describes an onboarding process with 5 phases. ' +
    'Key requirements include identity verification and compliance training.\n\n' +
    'El documento describe un proceso de onboarding con 5 fases. ' +
    'Los requisitos clave incluyen verificacion de identidad y capacitacion de cumplimiento.',
  entities: ['onboarding', 'compliance', 'identity verification', 'training'],
  confidence: 0.92,
  pages_analyzed: 12,
  processing_time_ms: 890,
}

export const DEMO_COPILOT_RESULT = {
  status: 'completed',
  recommendation:
    'Based on current market conditions, consider increasing allocation to fixed-income ' +
    'assets by 5% and reducing exposure to high-volatility sectors.\n\n' +
    'Basado en las condiciones actuales del mercado, considere aumentar la asignacion a ' +
    'activos de renta fija en un 5% y reducir la exposicion a sectores de alta volatilidad.',
  risk_score: 6.2,
  portfolio_value: 1250000,
  suggested_changes: [
    { asset: 'US Treasury Bonds', action: 'increase', delta: '+5%' },
    { asset: 'Tech Growth ETF', action: 'decrease', delta: '-3%' },
    { asset: 'Emerging Markets', action: 'decrease', delta: '-2%' },
  ],
  processing_time_ms: 2100,
}
