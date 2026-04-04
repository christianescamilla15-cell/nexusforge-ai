# Changelog — NexusForge AI

## v2.5.0 (2026-04-04)

### Superagent Upgrades (24 agents)
- All 24 agents upgraded with deterministic layers + LLM fallback
- `clean_llm_json()` handles markdown fences across all agents
- Pydantic v2 output schemas for 6 agents
- CircuitBreaker wired into BaseAgent.run()
- Tenacity retry catches all transient exceptions
- 6 critical bugs fixed (fail-open critic, EMA variance, DD/MM dates, etc.)

### New Pages
- Intelligence Hub (Enterprise Ops + Doc Intel + Analyze)
- System Status (real-time health of all components)
- API Docs (Swagger link + auth reference)
- Custom 404 page

### Auth & Security
- Email verification (OTP via Resend)
- Forgot Password flow (email code + reset)
- Change Password
- Google OAuth button
- Session expiry warning (5 min before JWT expires)
- Rate limiting per plan (Free 5, Pro 100, Team 500)
- RBAC ownership checks on DELETE endpoints
- API key encryption (XOR+HMAC)
- GDPR data export (JSON download)
- CORS configurable via env vars
- DEBUG=false by default

### UX Features (28 batches)
- React Router (URL-based navigation, deep linking)
- Code splitting (712KB → 342KB, 19 lazy chunks)
- Command Palette (Ctrl+K) with Quick Run automations
- Keyboard shortcuts (?, Ctrl+Enter, Esc)
- Getting Started checklist with completion celebration
- What's New changelog modal
- PWA manifest (installable on mobile)
- Dark mode for all components
- Top loading bar on route transitions
- Offline indicator
- Connection status dot in header
- Tab title with notification count + dynamic page names
- Window focus refetch (30s stale threshold)
- Skeleton loaders
- Sparkline + MiniBarChart components
- ConfirmModal (9/9 native confirms replaced)
- ErrorBoundary crash recovery
- Time-based greeting ("Good morning, Christian")
- Last page redirect on login
- Auto-refresh Dashboard (30s)

### Automations
- Search + pagination (12/page)
- Edit modal (name, description, trigger)
- Clone/duplicate
- Favorites (star + sort)
- Batch select + delete with Select All
- Share URL (clipboard)
- Schedule picker (presets + custom cron)
- Run notifications in all 5 dashboards
- CSV export for results
- Relative time (timeAgo)

### Dashboard
- Quick Actions (4 shortcut buttons)
- Plan usage bar
- Runs-per-day bar chart
- Getting Started checklist
- Auto-refresh with "updated ago" indicator
- KPI labels bilingual (ES/EN)
- Feedback widget (star rating)
- Platform stats in subtitle

### Workflows
- Export as JSON
- Import from JSON
- Duplicate
- Toast feedback on delete/rename

### Infrastructure
- Redis Upstash (TLS) on Render
- Zombie cleanup (auto every 5 min)
- Feedback persisted to PostgreSQL (migration 025)
- Email verified column (migration 026)

### Components Created (40)
IntelligenceHubPage, StatusPage, ApiDocsPage, CommandPalette, ConfirmModal, WhatsNew, KeyboardShortcuts, Skeleton, ErrorBoundary, Breadcrumb, CopyButton, TopLoadingBar, OfflineIndicator, SessionExpiry, Sparkline, MiniBarChart, GettingStarted, FeedbackWidget, SchedulePicker, NotFoundPage, ConnectionDot, EditAutomationModal, PlanUsageBar, BillingSection, AccountSection, TestAgentSection, EmptyState, manifest.json, useConfirm, useCopyClipboard, useCtrlEnter, useRefreshOnFocus, useTabTitle, timeAgo, clean_llm_json, output_schemas, circuit_breaker, encryption, deps, migrations

### Stats
- 106 modules, 260/260 tests, 16 pages, 342KB bundle
