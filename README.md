# NexusForge AI

Enterprise multi-agent orchestration platform for complex AI workflows.

## Overview
NexusForge AI is a production-oriented orchestration platform designed to coordinate specialized AI agents across complex workflows. It combines DAG-based execution, multi-agent routing, shared memory, self-healing recovery, RAG, and real-time monitoring.

## Why This Project Matters
Modern AI workflows break when orchestration, memory, retries, and provider routing are treated as afterthoughts. NexusForge explores how to build AI systems that behave more like reliable software platforms than isolated demos.

## Key Capabilities
- 22 specialized AI agents
- 6 swarm topologies (sequential, parallel, hierarchical, debate, consensus, adaptive)
- 3-tier memory system (working, episodic, semantic)
- Self-healing execution with 5 recovery strategies
- RAG-powered retrieval with Voyage AI + pgvector
- Multi-provider LLM routing with circuit breaker (Groq → Claude)
- REST API + WebSocket monitoring
- SDK + CLI support
- Terraform IaC + Kubernetes deployment

## System Architecture

```text
Web UI / CLI
    ↓
FastAPI Gateway
    ↓
DAG Executor + State Machine
    ↓
Agent Orchestrator
    ↓
Swarm Topologies (6 modes)
    ↓
Memory Layer + LLM Router
    ↓
PostgreSQL + pgvector / Redis
```

## Engineering Decisions

### Why DAG execution?
To support complex workflows with validation, retries, checkpointing, and non-linear agent coordination using Kahn's algorithm.

### Why external memory?
To keep agents stateless and modular, reducing context overload and enabling shared context across the swarm.

### Why multi-provider routing?
To improve resilience with circuit breaker pattern — automatic failover between Groq and Claude reduces outages.

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI |
| Database | PostgreSQL + pgvector |
| Cache | Redis |
| Embeddings | Voyage AI (512d) |
| LLM | Groq (Llama 3.3 70B), Claude |
| Infra | Docker, Terraform, Kubernetes |
| Frontend | React 18 + Vite |
| Monitoring | WebSocket real-time |

## Repo Structure
```
backend/          # FastAPI application
cli/              # Command-line interface
docs/             # Architecture documentation
frontend/         # React dashboard
infrastructure/   # Terraform + K8s configs
packages/sdk/     # TypeScript SDK
plugins/          # Plugin system
tests/            # 247 pytest tests
```

## Key Metrics
| Metric | Value |
|--------|-------|
| AI Agents | 22 |
| Swarm Topologies | 6 |
| Tests | 247 |
| Memory Tiers | 3 |
| Self-healing Strategies | 5 |
| Commits | 31 |

## How to Run
```bash
cp .env.example .env
docker compose up --build
```

### Main entry points
- **API**: `http://localhost:8000/docs`
- **CLI**: `python -m cli`
- **Frontend**: `http://localhost:3000`

## Case Study
→ [Architecture deep dive](docs/ARCHITECTURE.md)
→ [API Contract](docs/API_CONTRACT.md)

## Roadmap
- [ ] Evaluation harness for agent performance
- [ ] Latency benchmarking suite
- [ ] Observability dashboard
- [ ] Richer plugin ecosystem

---
Built by [Christian Hernandez](https://ch65-portfolio.vercel.app) · AI Engineer
