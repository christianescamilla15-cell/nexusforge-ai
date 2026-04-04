// ---------------------------------------------------------------------------
// NexusForge API Service — dual-mode: real backend or demo data.
// Mode is controlled via localStorage ('demo' or 'real').
// STRICT: Real mode NEVER falls back to demo data.
// ---------------------------------------------------------------------------

// ── Mode helpers (deprecated — always real mode) ───────────────────────────

/** @deprecated Always returns 'real'. Kept for backward compatibility. */
export function getMode() {
  return 'real'
}

/** Return the user-configured API URL (only relevant in real mode). Empty string = not configured. */
export function getApiUrl() {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem('nexusforge_api_url')
    || import.meta.env.VITE_API_URL
    || 'https://nexusforge-api.onrender.com/api'
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

/** @deprecated Always returns false. Kept for backward compatibility. */
export function isDemoMode() {
  return false
}

/**
 * Generic fetcher — calls backend, returns { data, error }.
 * On failure returns { data: null, error: "..." }.
 */
export async function fetchAPI(endpoint, options = {}) {
  const apiUrl = getApiUrl()
  if (!apiUrl) {
    return {
      data: null, isDemo: false,
      error: 'No API URL configured. Go to Settings to set the backend URL.',
    }
  }

  // Inject JWT token if available
  const token = typeof window !== 'undefined' ? localStorage.getItem('nf_token') : null
  const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {}

  try {
    const url = `${apiUrl}${endpoint}`
    console.log('[fetchAPI]', options.method || 'GET', url)
    const res = await fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...authHeaders, ...options.headers },
      signal: AbortSignal.timeout(30000),
      redirect: 'follow',
    })
    console.log('[fetchAPI] response status:', res.status, res.url)

    if (!res.ok) {
      let errDetail = `HTTP ${res.status}`
      try { const body = await res.json(); errDetail = body.detail || body.error || errDetail } catch {}
      console.error('[fetchAPI] error response:', errDetail)
      return { data: null, isDemo: false, error: `Backend error: ${errDetail}` }
    }

    return { data: await res.json(), isDemo: false, error: null }
  } catch (err) {
    console.error('[fetchAPI] fetch threw:', err)
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

// ── Guest trial tracking ────────────────────────────────────────

const GUEST_RUN_LIMIT = 10

/** Increment guest run counter. Returns { allowed, remaining } */
export function trackGuestRun() {
  try {
    const user = JSON.parse(localStorage.getItem('nf_user') || '{}')
    if (!user.isGuest) return { allowed: true, remaining: -1 } // unlimited for registered

    const runs = parseInt(localStorage.getItem('nf_guest_runs') || '0')
    if (runs >= GUEST_RUN_LIMIT) {
      return { allowed: false, remaining: 0 }
    }
    localStorage.setItem('nf_guest_runs', String(runs + 1))
    return { allowed: true, remaining: GUEST_RUN_LIMIT - runs - 1 }
  } catch {
    return { allowed: true, remaining: -1 }
  }
}

/** Get current guest usage */
export function getGuestUsage() {
  const runs = parseInt(localStorage.getItem('nf_guest_runs') || '0')
  return { used: runs, limit: GUEST_RUN_LIMIT, remaining: Math.max(0, GUEST_RUN_LIMIT - runs) }
}

// ── Demo datasets (kept for Playground/EnterpriseOps pages) ─────────────────

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
