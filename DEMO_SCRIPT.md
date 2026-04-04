# NexusForge AI — Demo Script (5 minutes)

> Use this script to showcase NexusForge in interviews, presentations, or portfolio reviews.

## Setup
- Open: https://frontend-silk-three-66.vercel.app
- Login with your account (or use Guest mode for quick demo)

---

## 1. Dashboard (30 sec)
**Show:** "Good morning, Christian" greeting, KPI cards animating, plan usage bar, quick actions

**Say:** "This is the main dashboard. KPIs auto-refresh every 30 seconds. The platform tracks 24 AI agents across 6 orchestration topologies."

**Do:** Point out the "Getting Started" checklist if visible. Click a Quick Action.

---

## 2. AI Wizard (60 sec)
**Show:** 5-step automation creation

**Say:** "Users describe what they want to automate in natural language. The AI designs the pipeline — selecting agents, setting dependencies, and configuring the dashboard."

**Do:**
1. Select "Ticket Triage"
2. Note how input/output auto-fill (smart defaults)
3. Show the pipeline preview
4. Publish → navigates to the typed dashboard

---

## 3. Run an Automation (60 sec)
**Show:** Typed dashboard (Ticket, Document, Email, or Report)

**Say:** "Each automation gets a specialized dashboard. Paste text, hit Ctrl+Enter, and the pipeline runs through the DAG — each agent handles its step."

**Do:**
1. Paste sample text
2. Press Ctrl+Enter (or click Run)
3. Watch the result appear
4. Show the notification bell

---

## 4. Intelligence Hub (45 sec)
**Show:** 3-tab layout (Enterprise Ops, Doc Intelligence, Analyze)

**Say:** "The Intelligence Hub combines our most powerful pipelines. Enterprise Ops runs 8 agents on any business text — classification, context, scheduling, CRM, notifications."

**Do:** Run Enterprise Ops with "I need to reschedule my appointment and my internet is down"

---

## 5. Command Palette (30 sec)
**Show:** Ctrl+K → search → Quick Run

**Say:** "Power users navigate with Ctrl+K. It searches all 17 pages plus your automations — you can jump to any dashboard or run an automation directly."

**Do:** Press Ctrl+K, type "ticket", show the Quick Run result, navigate.

---

## 6. Agent Architecture (45 sec)
**Show:** Agents page → click an agent → Test Agent section

**Say:** "Each of our 24 agents has 3 layers: deterministic rules first (instant, free), then LLM for complex cases, with a graceful fallback if everything fails. The circuit breaker automatically skips unhealthy agents."

**Do:** Open an agent, test inline with sample text, show the config options.

---

## 7. Technical Highlights (30 sec)
**Show:** Settings → Version (v2.5, 108 modules, 43 components)

**Say:**
- "44,000 lines of code, 260 passing tests"
- "Code splitting: 342KB initial bundle, 19 lazy chunks"
- "20 security features including HMAC webhooks, RBAC, API encryption"
- "Redis live for WebSocket, GZip compression, request tracing"

---

## Keyboard Shortcuts to Demo
- `Ctrl+K` — Command Palette
- `Ctrl+Enter` — Run automation
- `?` — Keyboard shortcuts
- `Esc` — Close any modal

## Key Technical Points for Interviews
1. **24 superagents** with deterministic-first architecture (90%+ free, LLM only for complex)
2. **Circuit breaker + self-healing** — agents auto-recover from failures
3. **React Router + code splitting** — 342KB initial, lazy-loads 19 page chunks
4. **40+ custom components** — Command Palette, ConfirmModal, Sparkline, Skeleton, ErrorBoundary
5. **Production security** — 8 headers per response, rate limiting, RBAC, encryption
6. **260/260 tests** — every commit verified
