# NexusForge AI

## What is this?
Enterprise-grade AI Agent Orchestration Platform with DAG-based workflow execution, 8+ specialized AI agents, multi-provider LLM routing, RAG with pgvector, Redis task queue, and real-time WebSocket monitoring.

## Stack
- Backend: Python 3.12 + FastAPI
- Database: PostgreSQL 16 + pgvector
- Document Store: MongoDB 7 (episodic memory, polyglot persistence)
- Cache/Queue: Redis 7
- LLM: Groq (primary) + Claude (fallback)
- Embeddings: Voyage AI (512d)
- Container: Docker Compose

## Commands
- `docker-compose up` — Start all services
- `cd backend && pytest` — Run tests
- Backend runs on http://localhost:8000
- API docs at http://localhost:8000/docs

## Conventions
- English for code, Spanish for user-facing strings
- Pydantic v2 for all models
- asyncpg for database operations
- Type hints on all functions
