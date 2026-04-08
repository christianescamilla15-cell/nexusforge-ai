# NexusForge AI — Project Summary

> Enterprise-grade AI Agent Orchestration Platform for PYMEs (SMBs)

## Live URLs
- **Frontend:** https://nexusforge-two.vercel.app
- **Backend API:** https://nexusforge-api.onrender.com/api
- **API Docs:** https://nexusforge-api.onrender.com/docs
- **GitHub:** https://github.com/christianescamilla15-cell/nexusforge-ai

## What it does
NexusForge lets businesses automate any workflow by combining 24 specialized AI agents. Users describe what they want in natural language, and the AI Wizard designs, builds, and deploys the automation — complete with a custom dashboard, results tracking, and integrations.

## Key Numbers
| Metric | Value |
|--------|-------|
| AI Agents | 24 superagents with deterministic + LLM layers |
| Swarm Topologies | 6 (sequential, parallel, hierarchical, debate, consensus, adaptive) |
| Frontend Pages | 16 URL-routed pages |
| Frontend Modules | 106 (19 lazy-loaded chunks) |
| Backend Endpoints | ~95 |
| Database Tables | 25+ (PostgreSQL + pgvector) |
| Tests | 260 passing |
| Bundle Size | 342KB (52% reduction via code splitting) |

## Tech Stack
- **Frontend:** React 19 + Vite 8 + React Router 7
- **Backend:** Python 3.12 + FastAPI
- **Database:** PostgreSQL 16 + pgvector (RAG)
- **Cache:** Redis 7 (Upstash, TLS)
- **LLM:** Groq (primary) + Claude (fallback)
- **Embeddings:** Voyage AI (512d)
- **Deploy:** Render (backend) + Vercel (frontend)

## Architecture Highlights

### 24 Superagents
Each agent has 3 layers:
1. **Deterministic** — regex, rules, Pydantic validation (instant, $0)
2. **LLM** — Groq/Claude with tenacity retry + circuit breaker
3. **Fallback** — always returns useful output, never crashes

Agents: Classifier, Extractor, Summarizer, Sentiment, Translator, OCR, Normalizer, Analyzer, Enricher, Compliance, Knowledge, Router, Validator, Reporter, Scraper, Webhook, Scheduler, Monitor, Planner, Researcher, Repair, Critic, Judge

### Self-Healing Pipeline
- Circuit breaker per agent (EMA health scoring)
- Error fingerprinting (cache known fixes)
- 5-level degradation (full → reduced → cached → template → honest failure)
- Zombie cleanup every 5 minutes

### Frontend UX (40 custom components)
- Command Palette (Ctrl+K) with automation Quick Run
- Code splitting (19 lazy chunks, 342KB initial)
- PWA installable
- Dark mode complete
- Keyboard-first (Ctrl+Enter, ?, Esc)
- Skeleton loaders, top loading bar, offline indicator
- Getting Started checklist with celebration
- Time-based greeting ("Good morning, Christian")
- Session expiry warning
- Tab title notification badges

### Auth & Security
- Email verification (OTP via Resend)
- Forgot/Reset password flow
- JWT + API key authentication
- Rate limiting per plan (Free 5/day, Pro 100, Team 500)
- RBAC ownership on destructive operations
- API key encryption at rest
- GDPR data export
- CORS configurable per environment

## What I Built (this session)
- 28 UX batches, ~82 commits
- 40 new components, 9 hooks/utilities
- 4 superagent upgrade batches
- Score improved from C+ to A
- Production verified: HEALTHY

## Skills Demonstrated
- Full-stack React + FastAPI development
- AI/LLM integration (multi-provider routing, circuit breaker)
- RAG pipeline (pgvector, semantic search)
- Multi-agent orchestration (6 topologies)
- Production deployment (Render + Vercel + Upstash)
- Security (bcrypt, HMAC-SHA256, JWT, RBAC, encryption)
- Performance (code splitting, lazy loading, EMA thresholds)
- UX engineering (Command Palette, keyboard shortcuts, dark mode, PWA)
- Testing (260 tests, continuous deployment)
