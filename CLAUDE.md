# NexusForge AI

## What is this?
Enterprise-grade AI Agent Orchestration Platform — 24 agents with dedicated local LLMs, chat-first interface with visible thinking, orchestrator memory, and LLM fallback chain.

## Stack
- Backend: Python 3.12 + FastAPI
- Frontend: React 18 + Vite 8
- Database: PostgreSQL 16 + pgvector (semantic memory)
- Document Store: MongoDB 7 (episodic memory)
- Cache/Queue: Redis 7 (working memory)
- Local LLMs: Ollama (deepseek-r1:8b, qwen2.5-coder:7b, llama3.1:8b, gemma3:4b, nomic-embed-text)
- Cloud LLMs: Groq (free fallback) + Claude API (paid last resort)
- Auth: Google OAuth + JWT + Stripe billing
- Deploy: Vercel (frontend) + Render (backend)

## Commands
- `cd backend && pytest` — Run 260+ tests
- `cd frontend && npx vite build` — Build frontend
- `nexusforge status` — Check all services
- `nexusforge dev` — Start local dev (Ollama + backend + frontend)
- `nexusforge kiro` — Generate Kiro specs

## Architecture
- Chat-first dashboard at / (ChatPanel 60% + PreviewPanel 40%)
- Classic dashboard at /dashboard-classic
- Per-agent model routing (gemma→classification, qwen→code, llama→language)
- LLM fallback: deepseek-r1 (local) → Groq (free cloud) → Claude (paid)
- 3-tier memory: working (Redis) → episodic (MongoDB) → semantic (pgvector)
- CORS middleware MUST be outermost (wraps AuthMiddleware 401s)
- Cloudflare tunnel exposes local Ollama to Render

## Critical Rules
- NEVER use PUT on Render /env-vars API without ALL existing vars (replaces everything)
- NEVER modify existing encapsulated components — add new ones alongside
- Quality over speed — read files before changing, build before pushing
- Frontend .jsx required for files with JSX (Vite 8 strict)
- Python not in PATH on this machine — use full path or sys.executable

## Deploy
- Render service: srv-d75b2575r7bs73b22gp0
- Render DB: dpg-d75b1cpr0fns73blrtdg-a
- Frontend: nexusforge-two.vercel.app (auto-deploy from master)
- Backend: nexusforge-api.onrender.com (auto-deploy from master)

## Conventions
- English for code, Spanish for user-facing strings
- Pydantic v2 for all models
- Type hints on all functions
- Chat system prompt: friendly, ONE question at a time, no JSON to user
