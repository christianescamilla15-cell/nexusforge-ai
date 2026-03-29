# NexusForge AI — Architecture Diagram (Enterprise-Grade)

## Full System Architecture

```text
┌───────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                               │
│                    Web Dashboard / CLI / API Consumer                │
└───────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌───────────────────────────────────────────────────────────────────────┐
│                           API LAYER                                  │
│                 FastAPI Gateway + REST + WebSockets                  │
└───────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                             │
│   Workflow Manager • DAG Executor • State Machine • Retry Policies   │
│      Checkpoints • Resume Logic • Failure Recovery • Routing         │
└───────────────────────────────────────────────────────────────────────┘
                │                        │                        │
                ▼                        ▼                        ▼
┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│ AGENT EXECUTION LAYER  │  │ MEMORY & RETRIEVAL     │  │ PROVIDER CONTROL       │
│ 22 Specialized Agents  │  │ Working Memory         │  │ Groq / Claude / others │
│ Swarm Topologies       │  │ Episodic Memory        │  │ Failover               │
│ Sequential / Parallel  │  │ Semantic Memory        │  │ Circuit Breaker        │
│ Debate / Review Loops  │  │ RAG / pgvector         │  │ Cost / Token Tracking  │
└────────────────────────┘  └────────────────────────┘  └────────────────────────┘
                │                        │                        │
                └───────────────┬────────┴───────────┬────────────┘
                                │                    │
                                ▼                    ▼
                     ┌───────────────────┐   ┌───────────────────┐
                     │ PostgreSQL        │   │ Redis             │
                     │ workflow_runs     │   │ event streaming   │
                     │ workflow_steps    │   │ caching           │
                     │ agent_events      │   │ pub/sub           │
                     │ checkpoints       │   │ transient state   │
                     │ evaluation_*      │   │                   │
                     └───────────────────┘   └───────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     OBSERVABILITY & EVALUATION                       │
│  Run History • Metrics • Timeline • Retries • Fallbacks • Quality   │
│  Evaluation Harness • Scenario Runner • Benchmarking • Reporting     │
└───────────────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### API Layer
FastAPI gateway exposing REST endpoints and WebSocket connections for real-time monitoring.

### Orchestration Layer
Coordinates workflows through DAG execution, state transitions, retry logic, checkpoint recovery, and topology-aware agent routing.

### Agent Execution Layer
Runs specialized agents across sequential, parallel, debate, review, and swarm-based execution patterns.

### Memory & Retrieval
Combines working, episodic, and semantic memory with pgvector-backed retrieval to support context sharing across runs and agents.

### Provider Control
Routes requests across multiple LLM providers with fallback behavior, circuit breaking, and cost-aware execution.

### Observability & Evaluation
Persists workflow history, step-level events, retries, fallback usage, and evaluation metrics for measurable system behavior.

## Database Schema

```text
workflow_runs ──┬── workflow_steps ──── agent_events
                ├── agent_events
                ├── checkpoints
                └── evaluation_runs ── evaluation_metrics
                         │
              evaluation_scenarios
```

## Data Flow

1. Client sends request → API Layer
2. Orchestrator creates workflow_run + plans DAG
3. Each agent step creates workflow_step + agent_events
4. On failure: retry → fallback → checkpoint → graceful degradation
5. On completion: aggregate metrics, persist results
6. Evaluation harness can replay scenarios and measure quality
