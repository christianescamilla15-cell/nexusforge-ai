# NexusForge AI v2.5

Enterprise-grade AI Agent Orchestration Platform for PYMEs — 44K lines, 108 modules, 260 tests.

NexusForge coordinates **24 superagents** (each with deterministic + LLM layers) across complex workflows using DAG execution, circuit breakers, self-healing, and 8 integrations. Features React Router with 17 pages, code splitting (342KB bundle), Command Palette (Ctrl+K), PWA, dark mode, and 20 security features.

| Metric | Value |
|--------|-------|
| Lines of code | 44,212 |
| Frontend modules | 108 (19 lazy chunks) |
| Backend endpoints | ~95 |
| Tests | 260/260 |
| Agents | 24 superagents |
| Components | 43 custom |
| Security features | 20 |

**Live Demo:** [frontend-silk-three-66.vercel.app](https://frontend-silk-three-66.vercel.app)
**API Docs:** [nexusforge-api.onrender.com/docs](https://nexusforge-api.onrender.com/docs)
**API Health:** [nexusforge-api.onrender.com/api/health](https://nexusforge-api.onrender.com/api/health)

---

## Why This Project Exists

Most AI applications break in production because orchestration, memory, retries, and observability are treated as afterthoughts. NexusForge explores how to design AI workflows that are **observable, resilient, and modular** — behaving more like reliable software platforms than isolated LLM calls.

---

## Platform Overview

```text
┌───────────────────────────────────────────────────────┐
│                    CLIENT LAYER                       │
│          Dashboard · Playground · Timeline · CLI      │
└───────────────────────────┬───────────────────────────┘
                            │
┌───────────────────────────┴───────────────────────────┐
│                     API LAYER                         │
│            FastAPI Gateway + WebSockets               │
└───────────────────────────┬───────────────────────────┘
                            │
┌───────────────────────────┴───────────────────────────┐
│                ORCHESTRATION LAYER                     │
│    DAG Executor · State Machine · Retry · Checkpoint  │
└──────┬────────────────────┬──────────────────┬────────┘
       │                    │                  │
┌──────┴──────┐  ┌──────────┴────────┐  ┌─────┴───────┐
│ AGENT SWARM │  │ MEMORY + RAG      │  │ LLM ROUTER  │
│ 22 agents   │  │ 3-tier + pgvector │  │ Groq/Claude │
│ 6 topologies│  │ working/episodic  │  │ circuit     │
│             │  │ semantic          │  │ breaker     │
└──────┬──────┘  └──────────┬────────┘  └─────┬───────┘
       │                    │                  │
       └────────────────────┼──────────────────┘
                            │
┌───────────────────────────┴───────────────────────────┐
│              PostgreSQL + Redis                        │
│    workflow_runs · steps · events · checkpoints       │
└───────────────────────────────────────────────────────┘
                            │
┌───────────────────────────┴───────────────────────────┐
│           OBSERVABILITY + EVALUATION                   │
│  Timeline · Traces · Metrics · Cost · 16 Scenarios    │
└───────────────────────────────────────────────────────┘
```

---

## Real Use Cases

### Enterprise Operations Assistant — 8 Agents
Processes customer requests end-to-end: intent classification, CRM lookup, document retrieval, meeting scheduling, CRM updates, team notifications, and supervisor validation.

| Agent | Role |
|-------|------|
| IntakeAgent | Validates and normalizes requests |
| IntentClassifierAgent | Classifies intent (6 categories) |
| CustomerContextAgent | Retrieves CRM customer data |
| DocumentRAGAgent | Searches knowledge base for policies |
| SchedulerAgent | Handles meeting rescheduling |
| CRMUpdateAgent | Logs interaction to CRM |
| NotificationAgent | Sends internal notifications |
| SupervisorAgent | Generates final response |

**API:** `POST /api/enterprise-ops/process`

### Document Intelligence — 7 Agents
Processes business documents into structured, validated outputs: contracts, policies, invoices, resumes, and reports.

| Agent | Role |
|-------|------|
| DocumentIngestionAgent | Receives and normalizes documents |
| DocumentClassifierAgent | Classifies document type |
| SchemaExtractionAgent | Extracts structured fields |
| ValidationAgent | Validates against business rules |
| SummaryAgent | Generates bilingual summary |
| StorageAgent | Persists to knowledge base |
| SupervisorAgent | Quality review + human escalation |

**API:** `POST /api/document-intelligence/run`

### Portfolio Intelligence Copilot — 6 Agents
Answers questions about portfolio projects, skills, and experience using retrieval and multi-step reasoning.

| Agent | Role |
|-------|------|
| RouterAgent | Classifies question type |
| PortfolioRAGAgent | Retrieves relevant projects |
| ProjectComparisonAgent | Compares projects technically |
| SkillsMapperAgent | Maps skills across portfolio |
| ResponseFormatterAgent | Formats structured answer |
| SupervisorAgent | Validates response quality |

**API:** `POST /api/portfolio-copilot/run`

---

## Core Infrastructure

### Workflow Engine
- DAG execution with Kahn's algorithm
- 6 swarm topologies (sequential, parallel, hierarchical, debate, consensus, adaptive)
- Checkpoint/resume for long-running workflows
- Step-level retry policies

### Memory Architecture
- **Working Memory** — in-process, sub-millisecond
- **Episodic Memory** — Redis, 30-day TTL, learns from past runs
- **Semantic Memory** — pgvector, permanent, 512d vectors

### LLM Router
- Groq (Llama 3.3 70B) primary, Claude fallback
- Circuit breaker pattern for automatic failover
- Token + cost tracking per request

### Reliability Layer
5 self-healing strategies wired into the engine:
1. Retry with exponential backoff
2. Skip with default output
3. Repair via RepairAgent
4. Escalate to human review
5. Fallback from cache

### Observability
- **Execution Timeline** — LangSmith-style step-by-step traces
- **Step Inspector** — input/output/tokens/latency/provider per step
- **Cost Dashboard** — token usage, cost in USD, per-agent breakdown
- **Persistent storage** — PostgreSQL-backed workflow_runs, steps, events, checkpoints

### Evaluation Harness
- 16 scenarios across 3 suites
- Quality scoring (0-100), latency metrics, success rates
- Retry/fallback counting, run comparisons

---

## Frontend Dashboard

14 pages covering the full platform:

| Page | Description |
|------|-------------|
| Dashboard | System health, KPIs, recent runs |
| Workflows | Workflow list and management |
| Agents | 22 registered agents with config |
| Executions | Run history with status filtering |
| Memory | 3-tier memory visualization |
| Documents | Document management + semantic search |
| Swarms | 6 topology visualizations |
| Healing | Self-healing simulation + strategies |
| Playground | Interactive workflow execution |
| Timeline | LangSmith-style execution traces |
| Cost Metrics | Token + cost dashboard |
| Evaluations | 16 scenarios + results + comparisons |
| Enterprise Ops | Operations Assistant UI |
| Settings | Demo/Real mode toggle + API config |

**Bilingual:** Full ES/EN support with language toggle.
**Demo Mode:** Works without backend using realistic demo data.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Database | PostgreSQL + pgvector |
| Cache | Redis |
| Embeddings | Voyage AI (512d) |
| LLM | Groq (Llama 3.3 70B), Claude |
| Frontend | React 18 + Vite |
| Infra | Docker, Docker Compose |
| Deploy | Vercel (frontend), Render-ready (backend) |
| Monitoring | WebSocket streaming |
| Testing | pytest (62+ tests) |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| AI Agents | 22 platform + 21 use-case agents |
| Swarm Topologies | 6 |
| Memory Tiers | 3 |
| Self-healing Strategies | 5 |
| Real Use Cases | 3 |
| Evaluation Scenarios | 16 |
| Tests | 62+ |
| API Routers | 16 |
| Frontend Pages | 14 |
| SQLAlchemy Models | 8 |

---

## Running Locally

```bash
git clone https://github.com/christianescamilla15-cell/nexusforge-ai
cd nexusforge-ai

# Backend
cp backend/.env.example backend/.env
docker compose up --build

# Frontend
cd frontend
npm install
npm run dev
```

**Entry points:**
- API: `http://localhost:8000/docs`
- Dashboard: `http://localhost:5173`
- CLI: `python -m cli`

---

## Engineering Decisions

### Why DAG execution instead of linear chains?
Complex workflows need branching, validation, retries, and checkpoints. DAG execution supports non-linear coordination.

### Why external memory instead of long prompts?
Agents stay stateless. Shared context lives in a 3-tier system — fast (Redis), persistent (PostgreSQL), semantic (pgvector).

### Why multiple LLM providers?
Circuit breaker + failover between Groq and Claude reduces single-provider dependency.

---

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — Full system architecture
- [design-decisions.md](docs/design-decisions.md) — 5 key architectural decisions
- [failure-recovery.md](docs/failure-recovery.md) — Layered recovery strategy
- [architecture-diagram.md](docs/architecture-diagram.md) — Enterprise-grade diagrams
- [IMPLEMENTATION_AUDIT.md](docs/IMPLEMENTATION_AUDIT.md) — Honest implementation audit

---

## Related Projects

Part of a broader AI systems portfolio:

- [MindScrolling](https://github.com/christianescamilla15-cell/MindScrolling) — AI-powered mobile product (Play Store)
- [FinanceAI Dashboard](https://github.com/christianescamilla15-cell/finance-ai-dashboard) — Financial analytics platform
- [Ad Analytics Pipeline](https://github.com/christianescamilla15-cell/ad-analytics-pipeline) — Marketing ETL platform
- [HRScout](https://github.com/christianescamilla15-cell/hr-scout-llm) — AI candidate screening
- [Playwright Automation](https://github.com/christianescamilla15-cell/playwright-automation) — Browser automation suite

**Portfolio:** [ch65-portfolio.vercel.app](https://ch65-portfolio.vercel.app)

---

## Author

**Christian Hernandez** — AI Systems Engineer

Multi-agent orchestration, LLM pipelines, AI product engineering, and data & analytics systems.

[GitHub](https://github.com/christianescamilla15-cell) · [Portfolio](https://ch65-portfolio.vercel.app) · [LinkedIn](https://linkedin.com/in/christianescamilla15-cell)
