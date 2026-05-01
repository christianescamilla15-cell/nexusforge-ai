/**
 * Component tests for PlatformSynthPage.
 *
 * The page coordinates three tightly-related responsibilities:
 *   1. Chat round-trip: user message → POST /platform-synth/chat
 *      → assistant message + spec + suggestions reflected in UI.
 *   2. Live template ranking: scores update as spec accumulates;
 *      incompatible templates render disabled.
 *   3. Build flow: select template + targetDir → green button
 *      activates → POST /platform-synth/build → result panel
 *      shows path/files/next_steps.
 *
 * fetch is mocked at the global level. We test what the user sees
 * through the rendered DOM, not implementation details.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import PlatformSynthPage from './PlatformSynthPage'

// jsdom doesn't implement Element.scrollIntoView. The page calls
// it on every chat update to scroll the bubble area to the latest
// message. Mock it before any test renders the page.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function () {}
}


// ─── fixtures ──────────────────────────────────────────────────


const TEMPLATES = [
  {
    template_id: 'fastapi_react_postgres',
    name: 'FastAPI + React + Postgres',
    short_description: 'Default Python+React stack',
    stack: ['python', 'fastapi', 'react', 'postgres'],
    best_for: ['saas', 'dashboard'],
  },
  {
    template_id: 'go_gin_postgres',
    name: 'Go + Gin + Postgres',
    short_description: 'Compiled Go API',
    stack: ['go', 'gin', 'postgres'],
    best_for: ['api', 'microservice'],
  },
]


function mockFetch(routes) {
  /**
   * routes: { 'GET /endpoint': () => responseObj, ... }
   * Each handler returns the JSON body. Status 200 is default.
   * For 4xx/5xx pass `[handler, statusCode]`.
   */
  global.fetch = vi.fn(async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase()
    // Find the matching route — endpoint string is the suffix
    // after the API root. We match on substring to ignore the
    // configurable host part.
    for (const [key, handler] of Object.entries(routes)) {
      const [routeMethod, routePath] = key.split(' ')
      if (method === routeMethod && url.endsWith(routePath)) {
        const result = typeof handler === 'function' ? handler(options) : handler
        const [body, status] = Array.isArray(result) ? result : [result, 200]
        return new Response(JSON.stringify(body), { status })
      }
    }
    return new Response(JSON.stringify({ detail: 'unmocked' }), { status: 404 })
  })
}


beforeEach(() => {
  localStorage.clear()
  // Pin API URL so getApiUrl() resolves deterministically in tests.
  localStorage.setItem('nexusforge_api_url', 'https://test-api.example.com/api')
  vi.restoreAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})


// ─── tests ─────────────────────────────────────────────────────


describe('PlatformSynthPage — initial render', () => {
  it('shows the title, subtitle, and chat input', async () => {
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
    })

    render(<PlatformSynthPage lang="en" />)
    expect(screen.getByText('Platform Synthesizer')).toBeTruthy()
    expect(
      screen.getByPlaceholderText(/Tell me what you're building/i)
    ).toBeTruthy()
  })

  it('fetches templates on mount and shows them in the right panel', async () => {
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
    })

    render(<PlatformSynthPage lang="en" />)

    // Both templates surface (initial scores are 0 because we haven't chatted).
    await waitFor(() => {
      expect(screen.getByText('FastAPI + React + Postgres')).toBeTruthy()
      expect(screen.getByText('Go + Gin + Postgres')).toBeTruthy()
    })
  })

  it('renders Spanish labels when lang="es"', async () => {
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
    })

    render(<PlatformSynthPage lang="es" />)
    expect(screen.getByText('Sintetizador de Plataformas')).toBeTruthy()
    expect(screen.getByPlaceholderText(/Dime qué estás construyendo/)).toBeTruthy()
  })
})


describe('PlatformSynthPage — chat round-trip', () => {
  it('sends user message, renders assistant reply, updates spec + suggestions', async () => {
    let chatCallCount = 0
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
      'POST /platform-synth/chat': () => {
        chatCallCount += 1
        return {
          assistant_message: 'Got it — Python it is. What feature?',
          spec: {
            project_name: 'inventory-tracker',
            language: 'python',
            features: [],
            integrations: [],
            notes: [],
          },
          template_suggestions: [
            {
              template: TEMPLATES[0],
              score: 0.55,
              matched_signals: ['language: python'],
            },
            {
              template: TEMPLATES[1],
              score: 0.0,
              matched_signals: ['language mismatch'],
            },
          ],
          next_question: null,
        }
      },
    })

    render(<PlatformSynthPage lang="en" />)
    await waitFor(() => screen.getByText('FastAPI + React + Postgres'))

    const input = screen.getByPlaceholderText(/Tell me what you're building/i)
    fireEvent.change(input, {
      target: { value: 'I want a Python dashboard for inventory' },
    })
    fireEvent.click(screen.getByText('Send'))

    // Assistant reply appears in the chat.
    await waitFor(() => {
      expect(screen.getByText('Got it — Python it is. What feature?')).toBeTruthy()
    })
    // Score updated visibly: 55%.
    await waitFor(() => {
      expect(screen.getByText('55%')).toBeTruthy()
    })
    // Spec preview includes the detected project_name.
    expect(screen.getByText(/"project_name": "inventory-tracker"/)).toBeTruthy()
    expect(chatCallCount).toBe(1)
  })

  it('disables Send button while a chat turn is in flight + shows "Thinking…"', async () => {
    let resolveChat
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
      'POST /platform-synth/chat': () =>
        new Promise(r => { resolveChat = r }).then(() => ({
          assistant_message: 'ok',
          spec: { features: [], integrations: [], notes: [] },
          template_suggestions: [],
          next_question: null,
        })),
    })

    render(<PlatformSynthPage lang="en" />)
    await waitFor(() => screen.getByText('FastAPI + React + Postgres'))

    const input = screen.getByPlaceholderText(/Tell me what you're building/i)
    fireEvent.change(input, { target: { value: 'hello' } })

    const sendButton = screen.getByText('Send')
    fireEvent.click(sendButton)

    // While in flight: button disabled, "Thinking…" indicator
    // visible (loading state). The input gets cleared on send so
    // checking button-enabled-after isn't meaningful — checking
    // the loading indicator is.
    await waitFor(() => {
      expect(sendButton.disabled).toBe(true)
      expect(screen.getByText(/Thinking/i)).toBeTruthy()
    })

    // Resolve the in-flight chat call. Loading clears, "Thinking…"
    // disappears.
    resolveChat()
    await waitFor(() => {
      expect(screen.queryByText(/Thinking/i)).toBeNull()
    })
  })

  it('surfaces backend errors without crashing', async () => {
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
      'POST /platform-synth/chat': [
        { detail: 'Chat extractor unavailable' },
        500,
      ],
    })

    render(<PlatformSynthPage lang="en" />)
    await waitFor(() => screen.getByText('FastAPI + React + Postgres'))

    fireEvent.change(
      screen.getByPlaceholderText(/Tell me what you're building/i),
      { target: { value: 'hi' } }
    )
    fireEvent.click(screen.getByText('Send'))

    // Error rendered to user.
    await waitFor(() => {
      expect(screen.getByText(/Backend error/i)).toBeTruthy()
    })
    // No exception thrown — page still renders.
    expect(screen.getByText('Platform Synthesizer')).toBeTruthy()
  })
})


describe('PlatformSynthPage — template selection + build flow', () => {
  it('Build button is disabled until template + project_name + targetDir are all set', async () => {
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
    })

    render(<PlatformSynthPage lang="en" />)
    await waitFor(() => screen.getByText('FastAPI + React + Postgres'))

    const buildBtn = screen.getByText('Build project')
    expect(buildBtn.disabled).toBe(true)
  })

  it('Build sends spec + selected template, renders success card on response', async () => {
    let buildCalledWith = null
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
      'POST /platform-synth/chat': () => ({
        assistant_message: 'Looks ready — pick a template.',
        spec: {
          project_name: 'inventory-tracker',
          language: 'python',
          backend_framework: 'fastapi',
          features: [],
          integrations: [],
          notes: [],
        },
        template_suggestions: [
          {
            template: TEMPLATES[0],
            score: 0.85,
            matched_signals: ['everything matches'],
          },
        ],
        next_question: null,
      }),
      'POST /platform-synth/build': (options) => {
        buildCalledWith = JSON.parse(options.body)
        return {
          project_path: '/home/user/nexusforge-generated/inventory-tracker',
          files_written: 13,
          template_id: 'fastapi_react_postgres',
          status: 'complete',
          next_steps: [
            'cd /home/user/nexusforge-generated/inventory-tracker',
            'pip install -r backend/requirements.txt',
          ],
          warnings: [],
          git_initialized: false,
          github_repo_url: null,
          post_build_warnings: [],
          mythos_ran: false,
          mythos_score: null,
          mythos_critical_count: 0,
          mythos_high_count: 0,
          mythos_findings_summary: [],
        }
      },
    })

    render(<PlatformSynthPage lang="en" />)
    await waitFor(() => screen.getByText('FastAPI + React + Postgres'))

    // 1. Chat to populate spec.
    fireEvent.change(
      screen.getByPlaceholderText(/Tell me what you're building/i),
      { target: { value: 'inventory tracker' } }
    )
    fireEvent.click(screen.getByText('Send'))

    // Wait for the suggestions to update (score ≥ 85%).
    await waitFor(() => screen.getByText('85%'))

    // 2. Click "Use this" on the template.
    fireEvent.click(screen.getAllByText('Use this')[0])
    await waitFor(() => screen.getByText('Selected'))

    // 3. targetDir auto-prefilled from project_name. Confirm by
    // checking the input value.
    const dirInput = screen.getByPlaceholderText(/nexusforge-generated/i)
    expect(dirInput.value).toMatch(/inventory-tracker/)

    // 4. Build button now enabled.
    const buildBtn = screen.getByText('Build project')
    expect(buildBtn.disabled).toBe(false)

    // 5. Click Build → result card appears.
    fireEvent.click(buildBtn)
    await waitFor(() => screen.getByText('Project generated'))
    expect(
      screen.getByText('/home/user/nexusforge-generated/inventory-tracker')
    ).toBeTruthy()
    expect(screen.getByText('13 files')).toBeTruthy()

    // 6. The build POST received the right payload.
    expect(buildCalledWith.template_id).toBe('fastapi_react_postgres')
    expect(buildCalledWith.spec.project_name).toBe('inventory-tracker')
    expect(buildCalledWith.target_dir).toMatch(/inventory-tracker/)
  })

  it('build options checkboxes pass flags through to /build POST body', async () => {
    let buildPayload = null
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
      'POST /platform-synth/chat': () => ({
        assistant_message: 'ready',
        spec: {
          project_name: 'with-flags',
          language: 'python',
          backend_framework: 'fastapi',
          features: [],
          integrations: [],
          notes: [],
        },
        template_suggestions: [
          { template: TEMPLATES[0], score: 0.85, matched_signals: [] },
        ],
        next_question: null,
      }),
      'POST /platform-synth/build': (options) => {
        buildPayload = JSON.parse(options.body)
        return {
          project_path: '/tmp/with-flags',
          files_written: 13,
          template_id: 'fastapi_react_postgres',
          status: 'complete',
          next_steps: [],
          warnings: [],
          git_initialized: true,
          git_first_commit_sha: 'abc123def4560000000000000000000000000000',
          github_repo_url: 'https://github.com/user/with-flags',
          post_build_warnings: [],
          mythos_ran: true,
          mythos_score: 100,
          mythos_critical_count: 0,
          mythos_high_count: 0,
          mythos_findings_summary: [],
        }
      },
    })

    render(<PlatformSynthPage lang="en" />)
    await waitFor(() => screen.getByText('FastAPI + React + Postgres'))

    fireEvent.change(
      screen.getByPlaceholderText(/Tell me what you're building/i),
      { target: { value: 'flagged build' } }
    )
    fireEvent.click(screen.getByText('Send'))
    await waitFor(() => screen.getByText('85%'))

    fireEvent.click(screen.getAllByText('Use this')[0])

    // Toggle all three flags ON.
    fireEvent.click(screen.getByLabelText(/Initialize git repo/i))
    // gh checkbox should be enabled now that git_init is true.
    const ghCheckbox = screen.getByLabelText(/Create GitHub repo/i)
    expect(ghCheckbox.disabled).toBe(false)
    fireEvent.click(ghCheckbox)
    // Visibility radio: pick public to verify it's not just the default.
    const publicRadio = screen.getByLabelText('Public')
    fireEvent.click(publicRadio)
    fireEvent.click(screen.getByLabelText(/Mythos pre-flight/i))

    fireEvent.click(screen.getByText('Build project'))
    await waitFor(() => screen.getByText('Project generated'))

    // The POST body received the toggled values, including the
    // non-default visibility choice.
    expect(buildPayload.git_init).toBe(true)
    expect(buildPayload.github_repo_create).toBe(true)
    expect(buildPayload.github_repo_visibility).toBe('public')
    expect(buildPayload.mythos_preflight).toBe(true)

    // Result card surfaces git/gh/mythos fields.
    expect(screen.getByText('First commit:')).toBeTruthy()
    expect(screen.getByText('abc123def456')).toBeTruthy()  // 12-char prefix
    expect(screen.getByText('https://github.com/user/with-flags')).toBeTruthy()
    expect(screen.getByText('100/100')).toBeTruthy()
  })

  it('GitHub repo checkbox is disabled when git_init is OFF', async () => {
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
    })

    render(<PlatformSynthPage lang="en" />)
    await waitFor(() => screen.getByText('FastAPI + React + Postgres'))

    const ghCheckbox = screen.getByLabelText(/Create GitHub repo/i)
    // Default state: git_init off, so gh is disabled (mirrors backend
    // contract: github_repo_create requires git_init).
    expect(ghCheckbox.disabled).toBe(true)

    fireEvent.click(screen.getByLabelText(/Initialize git repo/i))
    // Now gh becomes enabled.
    expect(ghCheckbox.disabled).toBe(false)
  })

  it('build defaults send all flags as false when no toggles touched', async () => {
    let buildPayload = null
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
      'POST /platform-synth/chat': () => ({
        assistant_message: 'ready',
        spec: {
          project_name: 'no-flags',
          features: [],
          integrations: [],
          notes: [],
        },
        template_suggestions: [
          { template: TEMPLATES[0], score: 0.85, matched_signals: [] },
        ],
        next_question: null,
      }),
      'POST /platform-synth/build': (options) => {
        buildPayload = JSON.parse(options.body)
        return {
          project_path: '/tmp/no-flags',
          files_written: 13,
          template_id: 'fastapi_react_postgres',
          status: 'complete',
          next_steps: [],
          warnings: [],
          git_initialized: false,
          github_repo_url: null,
          post_build_warnings: [],
          mythos_ran: false,
          mythos_score: null,
          mythos_critical_count: 0,
          mythos_high_count: 0,
          mythos_findings_summary: [],
        }
      },
    })

    render(<PlatformSynthPage lang="en" />)
    await waitFor(() => screen.getByText('FastAPI + React + Postgres'))

    fireEvent.change(
      screen.getByPlaceholderText(/Tell me what you're building/i),
      { target: { value: 'no flags here' } }
    )
    fireEvent.click(screen.getByText('Send'))
    await waitFor(() => screen.getByText('85%'))

    fireEvent.click(screen.getAllByText('Use this')[0])
    fireEvent.click(screen.getByText('Build project'))
    await waitFor(() => screen.getByText('Project generated'))

    expect(buildPayload.git_init).toBe(false)
    expect(buildPayload.github_repo_create).toBe(false)
    // Visibility default is 'private' — must be sent even though
    // gh is off, because the backend's BuildRequest schema accepts
    // the field unconditionally.
    expect(buildPayload.github_repo_visibility).toBe('private')
    expect(buildPayload.mythos_preflight).toBe(false)
  })

  it('disables incompatible templates ("Use this" button disabled when score=0)', async () => {
    mockFetch({
      'GET /platform-synth/templates': { templates: TEMPLATES },
      'POST /platform-synth/chat': () => ({
        assistant_message: 'Got it — Go.',
        spec: {
          language: 'go',
          features: [],
          integrations: [],
          notes: [],
        },
        template_suggestions: [
          {
            template: TEMPLATES[0],  // FastAPI — incompatible with Go
            score: 0.0,
            matched_signals: ['language mismatch'],
          },
          {
            template: TEMPLATES[1],  // Go+Gin — compatible
            score: 0.55,
            matched_signals: ['language: go'],
          },
        ],
        next_question: null,
      }),
    })

    render(<PlatformSynthPage lang="en" />)
    await waitFor(() => screen.getByText('FastAPI + React + Postgres'))

    fireEvent.change(
      screen.getByPlaceholderText(/Tell me what you're building/i),
      { target: { value: 'I want a Go API' } }
    )
    fireEvent.click(screen.getByText('Send'))

    await waitFor(() => screen.getByText('55%'))

    // Two "Use this" buttons; the FastAPI one should be disabled.
    const useButtons = screen.getAllByText('Use this')
    expect(useButtons).toHaveLength(2)
    // Order on the rendered DOM matches the suggestions array
    // (which we control above): FastAPI first, then Go.
    expect(useButtons[0].disabled).toBe(true)   // FastAPI
    expect(useButtons[1].disabled).toBe(false)  // Go+Gin
  })
})
