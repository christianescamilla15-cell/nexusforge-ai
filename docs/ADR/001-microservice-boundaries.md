# ADR-001: Microservice Boundaries

## Status

Accepted

## Context

NexusForge AI comprises multiple domains: workflow orchestration, agent execution, document indexing (RAG), swarm coordination, authentication, and tenant management. We need to decide how to decompose the system into deployable units.

A pure microservices architecture from day one introduces significant operational overhead (service discovery, distributed tracing, network latency, deployment complexity) while the team is small and the product is evolving rapidly. Conversely, a single monolith can become difficult to scale independently and creates tight coupling across domains.

## Decision

Start with a **modular monolith** implemented in FastAPI, with clear internal module boundaries that map to 8 logical service domains:

1. **Gateway** — API routing, rate limiting, CORS
2. **Auth** — JWT issuance, API key validation, RBAC
3. **Workflows** — DAG definition, validation, CRUD
4. **Orchestrator** — Execution engine, step scheduling, retry logic
5. **Agents** — Agent lifecycle, LLM integration, tool dispatch
6. **Documents** — Upload, chunking, embedding, vector search
7. **Swarms** — Multi-agent topology execution
8. **Tenants** — Tenant management, usage tracking

Each module exposes a clean internal API (Python imports) and communicates through well-defined interfaces. When scaling demands it, any module can be extracted into a standalone service behind the same API contract.

For local development, the monolith runs as a single FastAPI process. For production, it deploys via Docker Compose initially, with a Kubernetes migration path.

## Consequences

### Positive

- Rapid iteration: single deployment unit, no inter-service networking to manage
- Shared database transactions where needed (e.g., workflow creation + first run)
- Simple local development: `docker compose up` starts everything
- Clear extraction path: each module already has defined boundaries

### Negative

- All domains scale together initially (vertical scaling only)
- A failure in one module can affect the entire process
- Requires discipline to maintain module boundaries without a network wall

### Neutral

- Docker Compose for local/staging, Kubernetes manifests prepared for production extraction
- Monitoring is simpler (single process) but requires per-module instrumentation for visibility
