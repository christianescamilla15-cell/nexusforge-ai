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
  const stored = localStorage.getItem('nexusforge_api_url')
  const url = stored || import.meta.env.VITE_API_URL || 'https://nexusforge-api.onrender.com/api'

  // Prevent mixed content: force HTTPS in production
  if (typeof window !== 'undefined' && window.location.protocol === 'https:' && url.startsWith('http://') && !url.includes('localhost')) {
    return url.replace('http://', 'https://')
  }
  return url
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

// ── Token storage + refresh-token interceptor ──────────────────────────────
//
// T5 #4 (2026-04-30): paired with H-2 Phase 3 backend (commit ea6e217).
// When the deploy has ENABLE_REFRESH_TOKENS=true, the login response
// carries a 15-minute access token plus a 7-day refresh token. The
// interceptor in `fetchAPI` below catches the access token's 401-on-
// expiry, exchanges the refresh for a new pair via /auth/refresh, and
// retries the original request — invisible to the caller.
//
// Storage keys:
//   nf_token         — access JWT (Bearer header)
//   nf_refresh_token — opaque refresh token (Redis-backed on the server)
//
// Concurrency: a single refresh-in-flight promise is shared across all
// concurrent 401s so we never burn multiple refresh tokens on one
// expiry event. Refresh tokens are SINGLE-USE on the server — each
// /auth/refresh consumes the submitted token and issues a new one.

const NF_TOKEN_KEY = 'nf_token'
const NF_REFRESH_TOKEN_KEY = 'nf_refresh_token'

/** Read the current access JWT from localStorage. SSR-safe. */
export function getAccessToken() {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(NF_TOKEN_KEY)
}

/** Read the current refresh token from localStorage. SSR-safe. */
export function getRefreshToken() {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(NF_REFRESH_TOKEN_KEY)
}

/** Persist a fresh access (and optional refresh) token pair after login
 *  or refresh. Refresh-token-aware logins should call this instead of
 *  raw localStorage.setItem so future fields can be added in one place. */
export function setTokens({ token, refresh_token } = {}) {
  if (typeof window === 'undefined') return
  if (token) localStorage.setItem(NF_TOKEN_KEY, token)
  // refresh_token = null is a deliberate "the server failed to issue
  // one" signal; clear local copy so we stop attempting to refresh.
  if (refresh_token === null) localStorage.removeItem(NF_REFRESH_TOKEN_KEY)
  else if (refresh_token) localStorage.setItem(NF_REFRESH_TOKEN_KEY, refresh_token)
}

/** Wipe all auth state. Called on logout, on refresh failure, and any
 *  time the user is being bounced back to the login screen. */
export function clearTokens() {
  if (typeof window === 'undefined') return
  localStorage.removeItem(NF_TOKEN_KEY)
  localStorage.removeItem(NF_REFRESH_TOKEN_KEY)
}

let _refreshInFlight = null

/** Test-only: reset the in-flight refresh singleton between tests so
 *  module-level state doesn't leak across `it()` blocks. NOT for
 *  production callers — the in-flight dedup is the whole point of the
 *  module-level variable. Marked with the `__test__` prefix so it's
 *  never mistakenly imported from feature code. */
export function __test__resetRefreshState() {
  _refreshInFlight = null
}

/** Exchange the stored refresh token for a new (access, refresh) pair.
 *  Returns the new access token on success, or null on any failure
 *  (no refresh token, 401, 503, network). All concurrent callers
 *  share the same in-flight promise so one expiry == one refresh. */
async function _refreshAccessToken(apiUrl) {
  if (_refreshInFlight) return _refreshInFlight

  _refreshInFlight = (async () => {
    const refresh = getRefreshToken()
    if (!refresh) return null
    try {
      const res = await fetch(`${apiUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
        signal: AbortSignal.timeout(15000),
      })
      if (!res.ok) {
        // 401 = token expired/revoked. 503 = ENABLE_REFRESH_TOKENS off.
        // Either way, clear local state — the user must re-login.
        clearTokens()
        return null
      }
      const data = await res.json()
      // The server may return `refresh_token: null` if Redis flaked
      // mid-flight (it issues an access-only response in that case).
      // setTokens handles both — `null` clears the stored refresh.
      setTokens({ token: data.token, refresh_token: data.refresh_token })
      return data.token || null
    } catch {
      // Network error during refresh — DON'T clear tokens (user might
      // be temporarily offline; their original access token might
      // still work later). Just return null so the original request
      // surfaces the underlying error to the caller.
      return null
    } finally {
      _refreshInFlight = null
    }
  })()

  return _refreshInFlight
}

/**
 * Generic fetcher — calls backend, returns { data, error }.
 * On failure returns { data: null, error: "..." }.
 *
 * Refresh-token-aware: a 401 response triggers a single refresh
 * attempt (shared across concurrent callers). If refresh succeeds
 * the original request is retried once with the new access token;
 * if refresh fails the 401 propagates as an error and tokens are
 * cleared so the next page-load redirects to /login.
 */
export async function fetchAPI(endpoint, options = {}) {
  const apiUrl = getApiUrl()
  if (!apiUrl) {
    return {
      data: null, isDemo: false,
      error: 'No API URL configured. Go to Settings to set the backend URL.',
    }
  }

  const _doFetch = async (token) => {
    const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {}
    const url = `${apiUrl}${endpoint}`
    return fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...authHeaders, ...options.headers },
      signal: AbortSignal.timeout(30000),
      redirect: 'follow',
    })
  }

  try {
    let token = getAccessToken()
    let res = await _doFetch(token)

    // 401 + we have a refresh token + we haven't already retried the
    // /auth/refresh exchange itself → try refresh, then retry once.
    // The endpoint check guards against an infinite loop if /auth/refresh
    // itself returns 401 (then refresh would re-call refresh forever).
    if (res.status === 401 && token && endpoint !== '/auth/refresh') {
      const refreshed = await _refreshAccessToken(apiUrl)
      if (refreshed) {
        res = await _doFetch(refreshed)
      }
    }

    if (!res.ok) {
      let errDetail = `HTTP ${res.status}`
      try { const body = await res.json(); errDetail = body.detail || body.error || errDetail } catch {}
      return { data: null, isDemo: false, error: `Backend error: ${errDetail}` }
    }

    return { data: await res.json(), isDemo: false, error: null }
  } catch (err) {
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

