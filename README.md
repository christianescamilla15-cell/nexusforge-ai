# NexusForge AI

Enterprise multi-agent orchestration platform for building resilient AI workflows.

NexusForge AI is an experimental platform designed to coordinate specialized AI agents across complex workflows using orchestration, shared memory, and failure recovery mechanisms.

The goal is to explore how AI systems can behave more like reliable software platforms rather than isolated LLM calls.

---

## Why This Project Exists

Most AI applications break in production because orchestration, memory, retries, and observability are treated as afterthoughts.

Typical problems include:

- brittle agent chains
- context loss between steps
- provider failures
- lack of monitoring
- unpredictable execution paths

NexusForge explores how to design AI workflows that are **observable, resilient, and modular**.

---

## Core Capabilities

- Multi-agent orchestration
- DAG-based workflow execution
- Swarm agent topologies
- Self-healing execution strategies
- Shared vector memory
- Retrieval-augmented pipelines (RAG)
- Multi-provider LLM routing
- Observability and execution streaming

---

## System Architecture (Simplified)

```text
Client / UI
      ↓
FastAPI Gateway
      ↓
Orchestrator Engine
      ↓
Agent Swarm
      ↓
Shared Memory Layer
      ↓
PostgreSQL + Redis
```

Full architecture diagram:

```text
Web UI / CLI
      ↓
FastAPI Gateway
      ↓
DAG Executor + State Machine
      ↓
Agent Orchestrator
      ↓
Swarm Topologies
      ↓
Memory Layer (working / episodic / semantic)
      ↓
LLM Router + Circuit Breaker
      ↓
PostgreSQL / pgvector + Redis
```

---

## Agent Topologies

NexusForge experiments with multiple coordination models.

Examples:

- Sequential chain
- Parallel agents
- Reviewer loops
- Debate agents
- Swarm orchestration
- Hybrid DAG workflows

These topologies allow different strategies depending on task complexity.

---

## Memory Architecture

The platform implements a **three-tier memory model**.

### Working Memory
Short-term execution context shared across agents.

### Episodic Memory
Execution history and checkpoints.

### Semantic Memory
Vector database storage using **pgvector** for retrieval.

---

## Failure Recovery

AI workflows often fail due to:

- tool failures
- provider outages
- invalid responses
- context overflow

NexusForge introduces several resilience strategies:

- Retry policies
- Fallback LLM providers
- Circuit breakers
- Checkpoint / resume
- Agent re-routing

---

## Observability

The system exposes execution signals through:

- WebSocket streaming
- Redis pub/sub events
- Execution state tracking
- Cost / token monitoring

This enables real-time monitoring of agent workflows.

---

## Technology Stack

**Core:**
Python · FastAPI · PostgreSQL · pgvector · Redis · Docker

**AI Integration:**
Groq · Claude · LLM APIs

**Infrastructure:**
Docker · WebSockets · Async orchestration

---

## Repository Structure

```
backend/
  agents/         → agent implementations
  orchestrator/   → workflow execution engine
  memory/         → shared memory layers
  rag/            → indexing and retrieval
  providers/      → LLM routing and fallbacks
  tests/          → system validation

cli/              → command line interface

frontend/         → monitoring dashboard

docs/             → architecture documentation
```

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Agents implemented | 22 |
| Swarm topologies tested | 6 |
| Test cases | 247 |
| Architecture modules | orchestration, memory, routing, recovery |

---

## Running Locally

```bash
git clone https://github.com/christianescamilla15-cell/nexusforge-ai
cd nexusforge-ai
cp .env.example .env
docker compose up --build
```

Once running, you can access:
- API endpoints
- CLI interface
- Monitoring dashboard

---

## Demo Scenarios

Suggested demo flows:

### 1. Agent workflow execution
Run a simple multi-agent pipeline.

### 2. Swarm orchestration
Trigger parallel agent execution.

### 3. Failure recovery
Simulate provider failure and observe fallback routing.

---

## Engineering Decisions

### Why DAG execution instead of linear chains?
Complex AI workflows require branching, validation, retries, and checkpoints. DAG execution provides flexibility for non-linear workflows.

### Why external memory instead of prompt-only context?
Keeping memory external reduces context window limitations and enables shared state across agents.

### Why multiple LLM providers?
Provider routing enables resilience and reduces dependency on a single API.

---

## Current Limitations

This project is experimental and still evolving.

Known limitations include:

- Limited benchmarking data
- Evaluation harness still in progress
- Observability dashboards under development
- Plugin ecosystem early stage

---

## Future Work

Planned improvements:

- [ ] Evaluation framework for agent workflows
- [ ] Latency benchmarking
- [ ] Advanced observability dashboards
- [ ] Plugin marketplace for agents
- [ ] Improved cost monitoring

---

## Related Projects

Part of a broader AI systems portfolio:

- [MindScrolling](https://github.com/christianescamilla15-cell/MindScrolling) — AI-powered mobile product
- [Ad Analytics Pipeline](https://github.com/christianescamilla15-cell/ad-analytics-pipeline) — Marketing analytics platform
- [HRScout](https://github.com/christianescamilla15-cell/hr-scout-llm) — AI candidate screening workflow

**Portfolio:** [ch65-portfolio.vercel.app](https://ch65-portfolio.vercel.app)

---

## Author

**Christian Hernandez** — AI Systems Engineer

Focused on multi-agent orchestration, AI product engineering, LLM pipelines, and data & analytics systems.

[GitHub](https://github.com/christianescamilla15-cell) · [Portfolio](https://ch65-portfolio.vercel.app) · [LinkedIn](https://linkedin.com/in/christianescamilla15-cell)
