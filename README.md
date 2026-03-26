# NexusForge AI -- Enterprise Agent Orchestration Platform

![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![License: MIT](https://img.shields.io/badge/License-MIT-green)

NexusForge AI is an enterprise-grade platform for orchestrating multi-agent AI workflows. It provides a DAG-based execution engine, eight specialized agents, multi-provider LLM routing with circuit-breaker failover, RAG-powered document retrieval, real-time WebSocket monitoring, and automatic cost tracking -- all exposed through a production-ready REST API.

## Architecture

```mermaid
graph TB
    subgraph Clients
        UI[Web UI / CLI]
        WS[WebSocket Client]
    end

    subgraph API Layer
        FW[FastAPI]
    end

    subgraph Engine
        DAG[DAG Validator]
        EX[Executor]
        SM[State Machine]
        RP[Retry Policy]
        CP[Checkpoint]
    end

    subgraph Agents
        CL[Classifier]
        EXT[Extractor]
        SUM[Summarizer]
        AN[Analyzer]
        EN[Enricher]
        VAL[Validator]
        REP[Reporter]
        FIX[Repair]
    end

    subgraph LLM Router
        CB[Circuit Breaker]
        GR[Groq Provider]
        CLA[Claude Provider]
        TT[Token Tracker]
    end

    subgraph RAG Pipeline
        IDX[Indexer / Chunker]
        EMB[Voyage Embeddings]
        RET[Retriever]
    end

    subgraph Data Stores
        PG[(PostgreSQL + pgvector)]
        RD[(Redis Pub/Sub)]
    end

    UI --> FW
    WS --> FW
    FW --> DAG
    FW --> EX
    EX --> SM
    EX --> RP
    EX --> CP
    EX --> Agents
    Agents --> CB
    CB --> GR
    CB --> CLA
    CB --> TT
    EN --> RET
    RET --> EMB
    IDX --> EMB
    IDX --> PG
    RET --> PG
    EX --> PG
    EX --> RD
    RD --> WS
```

## Features

- **DAG Execution Engine** -- topological sort, parallel group scheduling, cycle detection
- **8 Specialized Agents** -- classifier, extractor, summarizer, analyzer, enricher, validator, reporter, repair
- **Multi-Provider LLM Routing** -- Groq (primary) + Claude (fallback) with automatic failover
- **Circuit Breaker** -- per-provider error tracking with configurable thresholds and cooldowns
- **RAG Pipeline** -- document chunking, Voyage AI embeddings, pgvector similarity search
- **WebSocket Streaming** -- real-time execution events via Redis pub/sub
- **Checkpoint & Resume** -- resume interrupted runs from the last completed step
- **Cost Tracking** -- per-request token counting and USD cost calculation
- **Self-Healing** -- RepairAgent diagnoses failures and suggests automatic fixes

## Tech Stack

| Layer        | Technology                          |
|-------------|-------------------------------------|
| API         | FastAPI 0.115, Pydantic v2          |
| Runtime     | Python 3.12, uvicorn                |
| Database    | PostgreSQL 16 + pgvector            |
| Cache/PubSub| Redis 7                             |
| LLM         | Groq (Llama), Anthropic Claude      |
| Embeddings  | Voyage AI                           |
| Containers  | Docker Compose                      |
| Testing     | pytest, pytest-asyncio              |

## Project Structure

```
nexusforge/
  backend/
    app/
      agents/            # 8 agent implementations + registry
        base.py          # BaseAgent ABC + AgentResult
        registry.py      # Agent type registry
        classifier.py    # Document classifier
        extractor.py     # Data extractor
        summarizer.py    # Text summarizer
        analyzer.py      # Deep analyzer
        enricher.py      # Data enricher (RAG)
        validator.py     # Quality gate
        reporter.py      # Report generator
        repair.py        # Self-healing repair
      engine/            # DAG execution engine
        dag.py           # DAG validation + parallel groups
        executor.py      # Workflow runner
        state_machine.py # Valid state transitions
        retry_policy.py  # Exponential backoff
        checkpoint.py    # Resume support
        step_runner.py   # Individual step execution
      llm/               # Multi-provider LLM routing
        router.py        # Router + circuit breaker
        provider.py      # Abstract provider interface
        groq_provider.py # Groq integration
        claude_provider.py # Claude integration
        token_tracker.py # Cost calculation
      rag/               # Document retrieval
        indexer.py       # Chunking + embedding storage
        retriever.py     # Semantic search
        embeddings.py    # Voyage AI embeddings
      routes/            # API endpoints
        health.py        # Health check
        workflows.py     # Workflow CRUD
        executions.py    # Execution management + WS
        agents.py        # Agent listing
        documents.py     # Document upload + search
      websocket/
        manager.py       # WebSocket connection manager
      db/
        client.py        # asyncpg pool + Redis client
      config.py          # Settings (pydantic-settings)
      main.py            # FastAPI app entrypoint
    tests/               # 75 tests
    requirements.txt
  docker-compose.yml
```

## Quick Start

### With Docker Compose

```bash
# Clone and enter the project
git clone https://github.com/your-org/nexusforge.git
cd nexusforge

# Create .env file
cp .env.example .env
# Edit .env with your API keys: GROQ_API_KEY, ANTHROPIC_API_KEY, VOYAGE_API_KEY

# Start all services
docker compose up -d

# API is available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Local Development

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API (requires PostgreSQL and Redis running)
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method    | Path                        | Description                       |
|----------|-----------------------------|-----------------------------------|
| GET      | `/api/health`               | Health check (DB, Redis, agents)  |
| POST     | `/api/workflows/`           | Create workflow (validates DAG)   |
| GET      | `/api/workflows/`           | List workflows (paginated)        |
| GET      | `/api/workflows/{id}`       | Get workflow by ID                |
| PUT      | `/api/workflows/{id}`       | Update workflow                   |
| DELETE   | `/api/workflows/{id}`       | Archive workflow (soft delete)    |
| POST     | `/api/executions/`          | Trigger workflow execution        |
| GET      | `/api/executions/`          | List runs (filter by status)      |
| GET      | `/api/executions/{id}`      | Get run with step details         |
| DELETE   | `/api/executions/{id}`      | Cancel running execution          |
| WS       | `/api/executions/ws/{id}`   | Live execution stream             |
| GET      | `/api/agents/`              | List all registered agents        |
| GET      | `/api/agents/{type}`        | Get agent details                 |
| POST     | `/api/documents/`           | Upload and index document         |
| GET      | `/api/documents/`           | List documents                    |
| POST     | `/api/documents/search`     | Semantic search (RAG)             |

## Agent Types

| Agent       | Purpose                                                         |
|------------|-----------------------------------------------------------------|
| classifier | Classifies documents into categories (legal, financial, etc.)   |
| extractor  | Extracts structured data from unstructured text                 |
| summarizer | Generates concise summaries of long documents                   |
| analyzer   | Performs sentiment analysis, trend detection, anomaly finding    |
| enricher   | Cross-references external sources and knowledge base (RAG)      |
| validator  | Quality gate -- validates completeness and accuracy              |
| reporter   | Generates formatted reports from workflow results               |
| repair     | Diagnoses failures and suggests self-healing fixes              |

## Testing

```bash
cd backend

# Run all 75 tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_dag.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing
```

Tests run without Docker, database, or API keys -- all external dependencies are mocked or use demo modes.

## Environment Variables

| Variable            | Description               | Default                                          |
|--------------------|---------------------------|--------------------------------------------------|
| `DATABASE_URL`     | PostgreSQL connection      | `postgresql://nexus:nexus_dev_2026@postgres:5432/nexusforge` |
| `REDIS_URL`        | Redis connection           | `redis://redis:6379`                             |
| `GROQ_API_KEY`     | Groq API key               | (empty -- agents fall back to demo mode)          |
| `ANTHROPIC_API_KEY`| Anthropic API key          | (empty -- used as fallback provider)              |
| `VOYAGE_API_KEY`   | Voyage AI embeddings key   | (empty -- required for RAG)                       |
| `DEBUG`            | Debug mode                 | `true`                                           |
| `ALLOWED_ORIGINS`  | CORS origins (comma-sep)   | `*`                                              |

## License

MIT
