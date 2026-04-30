/**
 * Tests for the refresh-token interceptor in services/api.js.
 *
 * T5 #4 (2026-04-30). The interceptor catches 401 responses, exchanges
 * the stored refresh token via /auth/refresh, then retries the
 * original request with the new access token. These tests pin that
 * contract using a stubbed `fetch`.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fetchAPI,
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  __test__resetRefreshState,
} from './api'

// Realistic test API URL — matches how the production app reads it.
const API_URL = 'https://test-api.example.com/api'

beforeEach(() => {
  localStorage.clear()
  // Pin the API URL so getApiUrl() resolves without env vars.
  localStorage.setItem('nexusforge_api_url', API_URL)
  vi.restoreAllMocks()
  // Reset module-level _refreshInFlight so a prior test's pending
  // promise doesn't dedupe into the current test.
  __test__resetRefreshState()
})

afterEach(() => {
  vi.restoreAllMocks()
})


// ─── token storage helpers ────────────────────────────────────────────


describe('token storage helpers', () => {
  it('setTokens persists both access and refresh tokens', () => {
    setTokens({ token: 'access-1', refresh_token: 'refresh-1' })
    expect(getAccessToken()).toBe('access-1')
    expect(getRefreshToken()).toBe('refresh-1')
  })

  it('setTokens with refresh_token=null clears the refresh slot', () => {
    setTokens({ token: 'a', refresh_token: 'r' })
    setTokens({ token: 'a2', refresh_token: null })
    expect(getAccessToken()).toBe('a2')
    expect(getRefreshToken()).toBeNull()
  })

  it('setTokens with refresh_token undefined leaves existing refresh in place', () => {
    // Common case: an endpoint returns only `token` (e.g. legacy
    // single-token deploy). The stored refresh, if any, must persist.
    setTokens({ token: 'a', refresh_token: 'r' })
    setTokens({ token: 'a2' })
    expect(getRefreshToken()).toBe('r')
  })

  it('clearTokens wipes both', () => {
    setTokens({ token: 'a', refresh_token: 'r' })
    clearTokens()
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })
})


// ─── refresh-token interceptor flow ───────────────────────────────────


describe('refresh-token interceptor', () => {
  it('does not attempt refresh when no token is stored', async () => {
    const fetchMock = vi.spyOn(global, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    )

    const result = await fetchAPI('/anything')

    // Single call, no Authorization header (no token).
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers).not.toHaveProperty('Authorization')
    expect(result.error).toBeNull()
  })

  it('passes Bearer token when access token is present', async () => {
    setTokens({ token: 'access-1' })
    const fetchMock = vi.spyOn(global, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    )

    await fetchAPI('/whoami')

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer access-1')
  })

  it('on 401, exchanges refresh and retries with new access token', async () => {
    setTokens({ token: 'expired', refresh_token: 'refresh-1' })

    const fetchMock = vi.spyOn(global, 'fetch')
      // 1st call: original request → 401
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'expired' }), { status: 401 })
      )
      // 2nd call: /auth/refresh → 200 with new pair
      .mockResolvedValueOnce(
        new Response(JSON.stringify({
          token: 'access-2',
          refresh_token: 'refresh-2',
          expires_in: 900,
        }), { status: 200 })
      )
      // 3rd call: retry of original request with new token → 200
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true, retry: true }), { status: 200 })
      )

    const result = await fetchAPI('/protected')

    expect(fetchMock).toHaveBeenCalledTimes(3)
    // 2nd call hit /auth/refresh
    expect(fetchMock.mock.calls[1][0]).toContain('/auth/refresh')
    // 3rd call retried the original endpoint with the NEW access token
    expect(fetchMock.mock.calls[2][0]).toContain('/protected')
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe('Bearer access-2')
    // Tokens persisted
    expect(getAccessToken()).toBe('access-2')
    expect(getRefreshToken()).toBe('refresh-2')
    // Caller sees the retried success body, not the 401.
    expect(result.error).toBeNull()
    expect(result.data).toEqual({ ok: true, retry: true })
  })

  it('on refresh 401, clears tokens and surfaces the original 401 to caller', async () => {
    setTokens({ token: 'expired', refresh_token: 'revoked' })

    vi.spyOn(global, 'fetch')
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'expired' }), { status: 401 })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'invalid refresh' }), { status: 401 })
      )

    const result = await fetchAPI('/protected')

    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
    expect(result.error).toBeTruthy()
    expect(result.error).toContain('expired')
  })

  it('on refresh 503 (ENABLE_REFRESH_TOKENS off), clears tokens', async () => {
    setTokens({ token: 'a', refresh_token: 'r' })

    vi.spyOn(global, 'fetch')
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'expired' }), { status: 401 })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Refresh tokens are not enabled' }), { status: 503 })
      )

    await fetchAPI('/protected')

    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })

  it('does not attempt refresh on 401 when no refresh token is stored', async () => {
    setTokens({ token: 'expired' })

    const fetchMock = vi.spyOn(global, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'expired' }), { status: 401 })
    )

    await fetchAPI('/protected')

    // Only the original request — no /auth/refresh attempt.
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('does not loop on /auth/refresh itself returning 401', async () => {
    // Simulate the (rare) case where /auth/refresh is called directly
    // and it returns 401 — the interceptor must NOT try to refresh
    // the refresh call. Only one fetch should happen.
    setTokens({ token: 'a', refresh_token: 'r' })

    const fetchMock = vi.spyOn(global, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'invalid' }), { status: 401 })
    )

    await fetchAPI('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: 'r' }),
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('persists new refresh_token=null when the server returns access-only', async () => {
    // Server quirk path (per backend routes.py:329-333): when Redis
    // flakes between consume and issue, /auth/refresh returns the new
    // access JWT but `refresh_token: null`. The interceptor must
    // accept that and clear the stored refresh slot so the next 401
    // doesn't try to use the now-consumed-and-revoked refresh token.
    setTokens({ token: 'expired', refresh_token: 'r1' })

    vi.spyOn(global, 'fetch')
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'expired' }), { status: 401 })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({
          token: 'access-2',
          refresh_token: null,  // server signal: refresh issue failed
          expires_in: 900,
        }), { status: 200 })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 })
      )

    const result = await fetchAPI('/protected')

    expect(result.error).toBeNull()
    expect(getAccessToken()).toBe('access-2')
    expect(getRefreshToken()).toBeNull()  // cleared per the null signal
  })
})
