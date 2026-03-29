# NexusForge AI

Enterprise multi-agent orchestration platform with DAG execution, self-healing workflows, shared memory, RAG, and multi-provider LLM routing.

---

## Why NexusForge Exists

LLM workflows fail in production because orchestration, retries, memory, and observability are often bolted on late. NexusForge explores how to build resilient multi-agent systems with explicit coordination, recovery, and memory design.

## Core Capabilities

- **22 specialized AI agents** with role-based routing
- **6 swarm topologies** — sequential, parallel, hierarchical, debate, consensus, adaptive
- **3-tier memory** — working (Redis), episodic (PostgreSQL), semantic (pgvector)
- **Self-healing execution** — 5 recovery strategies with checkpoint/resume
- **RAG retrieval** — Voyage AI embeddings + pgvector similarity search
- **Multi-provider LLM routing** — Groq primary, Claude fallback, circuit breaker pattern

## Architecture (simplified)

```text
Client / UI / CLI
       ↓
  FastAPI Gateway
       ↓
    Orchestrator
       ↓
   Agent Swarm (22 agents × 6 topologies)
       ↓
  Memory + Retrieval (pgvector + Redis)
       ↓
  PostgreSQL / Redis
```

> Full architecture details → [ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Engineering Decisions

### Why DAG execution instead of linear chaining?
Complex workflows need validation, retries, checkpointing, and non-linear agent coordination. Kahn's algorithm enables topological ordering with dependency resolution.

### Why external memory instead of long prompts?
Agents stay stateless and modular. Shared context lives in a 3-tier memory system — working memory in Redis (fast), episodic in PostgreSQL (persistent), semantic in pgvector (similarity search).

### Why Groq primary + Claude fallback?
Groq (Llama 3.3 70B) provides fast, free inference. Claude serves as quality fallback. Circuit breaker pattern handles provider outages automatically.

### Why Redis + PostgreSQL split?
Redis for hot state (agent working memory, pub/sub events). PostgreSQL for durable state (episodic memory, RAG index, execution history).

### Why checkpoint/resume?
Long-running agent workflows need recovery points. If an agent fails at step 7 of 12, the system resumes from the last checkpoint — not from scratch.

## Observability

NexusForge includes built-in monitoring for production debugging:

- **Live execution events** via WebSocket streaming
- **Provider failure tracking** with automatic failover logs
- **Retry behavior** visibility per agent per step
- **Checkpoint state** inspection and resume controls
- **Token usage and cost tracking** across providers

## Demo Scenarios

### 1. Run a simple agent workflow
```bash
python -m cli run --workflow simple --agents 3
```

### 2. Trigger a swarm topology execution
```bash
python -m cli swarm --topology hierarchical --task "analyze document"
```

### 3. Simulate provider failure and fallback recovery
```bash
python -m cli test-failover --primary groq --fallback claude
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Database | PostgreSQL + pgvector |
| Cache | Redis |
| Embeddings | Voyage AI (512d) |
| LLM Providers | Groq (Llama 3.3 70B), Claude (Anthropic) |
| Infra | Docker, Terraform, Kubernetes |
| Frontend | React 18 + Vite |
| Monitoring | WebSocket real-time streaming |
| SDK | TypeScript SDK + Python CLI |

## Code Structure

```
backend/app/agents       → agent implementations and registry
backend/app/orchestrator → DAG execution, routing, state machine
backend/app/memory       → working / episodic / semantic memory
backend/app/rag          → indexing, chunking, retrieval
backend/app/providers    → Groq / Claude routing + circuit breaker
backend/app/healing      → self-healing strategies
cli/                     → command-line interface
frontend/                → React monitoring dashboard
infrastructure/          → Terraform + Kubernetes configs
packages/sdk/            → TypeScript SDK
plugins/                 → plugin system
tests/                   → 247 pytest tests
docs/                    → ARCHITECTURE.md, API_CONTRACT.md
```

## Key Metrics

| Metric | Value |
|--------|-------|
| AI Agents | 22 |
| Swarm Topologies | 6 |
| Memory Tiers | 3 |
| Self-healing Strategies | 5 |
| Tests | 247 (pytest) |
| Commits | 31 |

## Current Limitations

- Benchmark latency not yet formalized across topologies
- Evaluation harness for agent quality still in progress
- Production observability dashboard planned but not shipped
- Plugin ecosystem still early — 2 plugins available

## How to Run

```bash
cp .env.example .env
docker compose up --build
```

| Entry Point | URL |
|-------------|-----|
| API Docs | `http://localhost:8000/docs` |
| CLI | `python -m cli` |
| Dashboard | `http://localhost:3000` |

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — full system architecture
- [API_CONTRACT.md](docs/API_CONTRACT.md) — endpoint specifications

## Roadmap

- [ ] Agent performance evaluation harness
- [ ] Latency benchmarking suite per topology
- [ ] Production observability dashboard
- [ ] Richer plugin ecosystem
- [ ] Multi-tenant agent isolation

---

Built by [Christian Hernandez](https://ch65-portfolio.vercel.app) · AI Systems Engineer
