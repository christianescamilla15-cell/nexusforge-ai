# NexusForge AI -- Enterprise Agent Orchestration Platform

![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Agents: 22](https://img.shields.io/badge/Agents-22-orange)
![Topologies: 6](https://img.shields.io/badge/Topologies-6-blueviolet)
![Tests: 231](https://img.shields.io/badge/Tests-231-brightgreen)

NexusForge AI is an enterprise-grade platform for orchestrating multi-agent AI workflows. It provides a DAG-based execution engine, 22 specialized agents, 6 swarm topologies, a 3-tier memory system, self-healing pipelines, a plugin architecture, multi-provider LLM routing with circuit-breaker failover, RAG-powered document retrieval, real-time WebSocket monitoring, and automatic cost tracking -- all exposed through a production-ready REST API.

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

    subgraph Agents["Agent Framework (22 agents)"]
        CL[Classifier]
        EXT[Extractor]
        SUM[Summarizer]
        AN[Analyzer]
        MORE["+18 more..."]
    end

    subgraph Swarms["Swarm Topologies (6)"]
        SEQ[Sequential]
        PAR[Parallel]
        HIER[Hierarchical]
        DEB[Debate]
        CON[Consensus]
        ADA[Adaptive]
    end

    subgraph Memory["3-Tier Memory"]
        WM[Working Memory]
        EM[Episodic Memory]
        SEM[Semantic Memory]
    end

    subgraph Healing["Self-Healing"]
        FD[Failure Detector]
        STR[Strategy Selector]
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

    subgraph Plugins
        PLG[Plugin Loader]
        GOV[Gov Data MX]
    end

    UI --> FW
    WS --> FW
    FW --> DAG
    FW --> EX
    EX --> SM
    EX --> RP
    EX --> CP
    EX --> Agents
    EX --> Swarms
    Agents --> CB
    Agents --> Memory
    CB --> GR
    CB --> CLA
    CB --> TT
    EX --> Healing
    Healing --> Agents
    WM -.-> EM -.-> SEM
    EM --> RD
    SEM --> PG
    EN --> RET
    RET --> EMB
    IDX --> EMB
    IDX --> PG
    RET --> PG
    EX --> PG
    EX --> RD
    RD --> WS
    PLG --> Agents
```

## Features

- **DAG Execution Engine** -- topological sort, parallel group scheduling, cycle detection
- **22 Specialized Agents** -- from classification and extraction to compliance checking and task planning
- **6 Swarm Topologies** -- sequential, parallel, hierarchical, debate, consensus, and adaptive orchestration
- **3-Tier Memory System** -- working (in-process), episodic (Redis, 30-day TTL), semantic (pgvector embeddings)
- **Self-Healing Pipelines** -- automatic failure detection, classification, and recovery with 5 strategies
- **Plugin Architecture** -- drop-in plugins for custom agents and data connectors
- **Multi-Provider LLM Routing** -- Groq (primary) + Claude (fallback) with automatic failover
- **Circuit Breaker** -- per-provider error tracking with configurable thresholds and cooldowns
- **RAG Pipeline** -- document chunking, Voyage AI embeddings, pgvector similarity search
- **WebSocket Streaming** -- real-time execution events via Redis pub/sub
- **Checkpoint & Resume** -- resume interrupted runs from the last completed step
- **Cost Tracking** -- per-request token counting and USD cost calculation

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
      agents/            # 22 agent implementations + registry
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
        normalizer.py    # Data normalizer
        researcher.py    # Multi-source researcher
        translator.py    # Language translator
        compliance.py    # Regulatory compliance
        monitor.py       # Pipeline health monitor
        router.py        # Intelligent task router
        critic.py        # Output quality critic
        planner.py       # Task decomposition planner
        knowledge.py     # RAG knowledge agent
        scraper.py       # Web data scraper
        ocr.py           # OCR text extraction
        sentiment.py     # Sentiment analysis
        scheduler.py     # Execution scheduler
        webhook.py       # Webhook dispatcher
      engine/            # DAG execution engine
        dag.py           # DAG validation + parallel groups
        executor.py      # Workflow runner
        state_machine.py # Valid state transitions
        retry_policy.py  # Exponential backoff
        checkpoint.py    # Resume support
        step_runner.py   # Individual step execution
      memory/            # 3-tier memory system
        working.py       # Tier 1: in-process dict
        episodic.py      # Tier 2: Redis (30-day TTL)
        semantic.py      # Tier 3: pgvector embeddings
        manager.py       # Unified memory manager
      swarms/            # 6 swarm topologies
        base.py          # BaseSwarm ABC + SwarmResult
        manager.py       # Topology registry
        sequential.py    # A -> B -> C pipeline
        parallel.py      # Fan-out / fan-in
        hierarchical.py  # Manager/worker pattern
        debate.py        # Multi-agent debate
        consensus.py     # Voting-based consensus
        adaptive.py      # Dynamic routing
      healing/           # Self-healing system
        detector.py      # Error classification
        strategies.py    # Recovery strategies
      plugins/           # Plugin architecture
        interface.py     # NexusPlugin ABC + PluginManifest
        loader.py        # Dynamic plugin discovery
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
    tests/               # 231 tests
    requirements.txt
  plugins/               # External plugins directory
    gov_data_mx/         # Mexico government data plugin
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

---

## Agent Framework (22 Agents)

All agents inherit from `BaseAgent` and implement `execute(input_data, config) -> AgentResult`. Each agent has a **demo mode** for testing without LLM calls and a **fallback path** when the LLM router is unavailable.

| Agent         | Type           | Description                                                                |
|--------------|----------------|----------------------------------------------------------------------------|
| Classifier   | `classifier`   | Classifies documents into categories: legal, financial, technical, medical, general |
| Extractor    | `extractor`    | Extracts named entities (people, orgs, dates, amounts, locations) from text |
| Summarizer   | `summarizer`   | Generates concise summaries with configurable length (short/medium/long)   |
| Analyzer     | `analyzer`     | Performs sentiment, topic, and complexity analysis on text                  |
| Enricher     | `enricher`     | Enriches extracted entities with additional context and cross-references    |
| Validator    | `validator`    | Quality gate: validates completeness, consistency, and accuracy            |
| Reporter     | `reporter`     | Generates structured markdown reports from all previous agent outputs      |
| Repair       | `repair`       | Analyzes failed workflow steps and suggests fixes for self-healing         |
| Normalizer   | `normalizer`   | Normalizes extracted data into consistent schema, deduplicates, standardizes |
| Researcher   | `researcher`   | Conducts multi-source research on a topic and returns summary with citations |
| Translator   | `translator`   | Translates text between languages with automatic source language detection  |
| Compliance   | `compliance`   | Checks text against regulatory rules and identifies compliance issues      |
| Monitor      | `monitor`      | Monitors pipeline health metrics and analyzes execution patterns           |
| Router Agent | `router_agent` | Intelligent task routing -- determines which agent(s) should handle a task  |
| Critic       | `critic`       | Evaluates output quality from other agents, provides scores and critiques  |
| Planner      | `planner`      | Decomposes complex tasks into subtasks and creates execution plans          |
| Knowledge    | `knowledge`    | Answers questions using RAG over processed documents and semantic memory    |
| Scraper      | `scraper`      | Collects and extracts structured data from web sources                     |
| OCR          | `ocr`          | Extracts text from images and scanned documents                            |
| Sentiment    | `sentiment`    | Analyzes sentiment, emotional tone, and opinion in text                    |
| Scheduler    | `scheduler`    | Suggests optimal execution scheduling for task pipelines                   |
| Webhook      | `webhook`      | Sends data to external systems via webhooks and reports delivery status     |

### 3-Tier Memory System

Agents share a unified memory system with three independent tiers:

```
Tier 1: Working Memory (in-process dict)
  - Fast, ephemeral, scoped to a single execution
  - Stores current task context, conversation history (last 20 messages), tool results
  - Destroyed when execution ends

Tier 2: Episodic Memory (Redis, 30-day TTL)
  - Medium-term storage of task summaries and success/failure patterns
  - Per-agent timeline of up to 500 episodes
  - Supports pattern analysis (success/failure rates by type)

Tier 3: Semantic Memory (pgvector)
  - Long-term knowledge store with vector embeddings
  - Similarity-based retrieval of past experiences
  - Cross-agent knowledge transfer support
```

The `MemoryManager` provides a unified API for storing and recalling across all tiers:

```python
await memory.remember(agent_id, text, tier="working,episodic")
results = await memory.recall(agent_id, query, tiers=["working", "semantic"])
context = await memory.build_context(agent_id, task)  # combines all tiers
```

---

## Swarm Topologies (6)

Swarms orchestrate multiple agents as a coordinated unit. Each topology defines how agents communicate and combine their outputs.

| Topology      | Pattern            | Description                                                              |
|--------------|--------------------|--------------------------------------------------------------------------|
| `sequential`  | A -> B -> C        | Pipeline: each agent's output feeds into the next agent's input          |
| `parallel`    | Fan-out / Fan-in   | All agents run simultaneously on the same input; results are combined    |
| `hierarchical`| Manager / Workers  | A manager agent delegates subtasks to worker agents and synthesizes results |
| `debate`      | Argue + Judge      | Multiple agents debate a topic; a judge agent selects the best argument  |
| `consensus`   | Vote + Merge       | Agents independently process input, then vote on the best approach       |
| `adaptive`    | Dynamic Routing    | A router agent dynamically selects agents based on input characteristics |

```mermaid
graph LR
    subgraph Sequential
        S1[A] --> S2[B] --> S3[C]
    end

    subgraph Parallel
        P0[Input] --> P1[A]
        P0 --> P2[B]
        P0 --> P3[C]
        P1 --> P4[Merge]
        P2 --> P4
        P3 --> P4
    end

    subgraph Hierarchical
        H1[Manager] --> H2[Worker A]
        H1 --> H3[Worker B]
        H2 --> H1
        H3 --> H1
    end
```

Usage:

```python
from app.swarms.manager import get_swarm, list_topologies

swarm = get_swarm("parallel")
result = await swarm.execute(
    input_data={"text": "Analyze this document"},
    agent_types=["classifier", "sentiment", "summarizer"],
    config={"demo": True},
)
# result.output  -> dict with each agent's output
# result.topology -> "parallel"
# result.agents_used -> ["classifier", "sentiment", "summarizer"]
```

---

## Self-Healing System

When a pipeline step fails, the self-healing system automatically detects, classifies, and attempts to recover from the error.

### Healing Flow

```mermaid
flowchart LR
    FAIL[Step Fails] --> DETECT[Failure Detector]
    DETECT --> CLASS[Classify Error]
    CLASS --> SELECT[Select Strategy]
    SELECT --> APPLY[Apply Strategy]
    APPLY --> OK{Success?}
    OK -- Yes --> RESUME[Resume Pipeline]
    OK -- No --> ESCALATE[Escalate to Human]
```

### Error Classification

The `FailureDetector` uses pattern matching to classify errors into types:

| Error Type       | Examples                                    | Recoverable | Default Action |
|-----------------|---------------------------------------------|-------------|----------------|
| `network`       | Connection refused, DNS resolution, 429     | Yes         | Retry          |
| `timeout`       | Request timed out, deadline exceeded        | Yes         | Retry          |
| `data_quality`  | Empty response, no data found, 404          | Yes         | Skip           |
| `schema_mismatch`| JSON parse error, validation failure       | Yes         | Repair         |
| `llm_error`     | Content filter, context length exceeded     | Yes         | Retry          |
| `unknown`       | Unrecognized error patterns                 | Depends     | Repair/Escalate|

### Recovery Strategies (5)

| Strategy    | Behavior                                                                   |
|------------|-----------------------------------------------------------------------------|
| **Retry**    | Re-execute with modified config (lower temperature, more tokens)          |
| **Skip**     | Use default/empty output and continue the pipeline                        |
| **Repair**   | Invoke RepairAgent to diagnose and generate a fix, then re-execute        |
| **Escalate** | Mark for human review and pause the pipeline                              |
| **Fallback** | Use cached result from a previous successful run                          |

---

## Plugin System

NexusForge supports drop-in plugins that extend the platform with custom agents and data connectors.

### How Plugins Work

1. Create a directory under `plugins/` with an `__init__.py`
2. Implement the `NexusPlugin` abstract class with `get_manifest()` and `register()`
3. The plugin loader discovers and loads plugins on startup
4. Agents and connectors provided by the plugin are added to the global registries

### Plugin Interface

```python
from app.plugins.interface import NexusPlugin, PluginManifest

class MyPlugin(NexusPlugin):
    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="my-plugin",
            version="1.0.0",
            description="Custom data connector",
            author="Your Team",
            agent_types=["custom_agent"],
            connectors=["api.example.com"],
        )

    def register(self, agent_registry, connector_registry=None):
        agent_registry("custom_agent", MyCustomAgent())

plugin = MyPlugin()  # module-level attribute required
```

### Example Plugins

| Plugin          | Description                                          | Agents                       | Connectors                               |
|----------------|------------------------------------------------------|------------------------------|------------------------------------------|
| `gov-data-mx`  | Mexico government open data (datos.gob.mx, CompraNet)| `datos-abierto`, `compranet` | `datos.gob.mx`, `compranet.hacienda.gob.mx` |

---

## Testing

```bash
cd backend

# Run all 231 tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_dag.py -v

# Run Session 3 tests only
python -m pytest tests/test_memory.py tests/test_swarms.py tests/test_healing.py tests/test_agents_extended.py tests/test_plugins.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing
```

Tests run without Docker, database, or API keys -- all external dependencies are mocked or use demo modes.

### Test Breakdown

| Test File              | Tests | Coverage Area                          |
|-----------------------|-------|----------------------------------------|
| `test_dag.py`         | 15    | DAG validation, parallel groups, cycles|
| `test_state_machine.py`| 17   | Workflow and step state transitions    |
| `test_agents.py`      | 10    | Core 8 agents, demo mode, fallback    |
| `test_agents_extended.py`| 84 | All 22 agents, metadata, demo execution|
| `test_memory.py`      | 17    | Working memory set/get/clear/context   |
| `test_swarms.py`      | 19    | 6 topologies, SwarmResult, execution   |
| `test_healing.py`     | 25    | Error classification, 5 strategies     |
| `test_plugins.py`     | 9     | PluginManifest, loader, abstract base  |
| `test_router.py`      | 9     | Circuit breaker, cost calculation      |
| `test_retry.py`       | 9     | Exponential backoff, non-retryable     |
| `test_models.py`      | 10    | Pydantic models, validation            |
| `test_rag.py`         | 5     | Text chunking                          |

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
