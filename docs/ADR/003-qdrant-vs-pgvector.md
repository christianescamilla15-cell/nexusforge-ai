# ADR-003: pgvector Over Qdrant for Vector Search

## Status

Accepted

## Context

The RAG (Retrieval-Augmented Generation) pipeline requires vector similarity search to find relevant document chunks given a query embedding. Two leading options were evaluated:

| Criteria | Qdrant | pgvector |
|---|---|---|
| Deployment | Separate service (Docker) | PostgreSQL extension |
| Performance (<1M vectors) | Excellent | Good (HNSW index) |
| Performance (>10M vectors) | Excellent | Degrades without tuning |
| Filtering | Native metadata filtering | SQL WHERE clauses |
| Operational cost | New service to monitor, backup, scale | Part of existing PostgreSQL |
| Consistency | Eventually consistent | ACID with relational data |

Our current dataset projection: <500K document chunks per tenant, <50 tenants in year one, totaling <25M vectors across all tenants (with tenant_id filtering reducing per-query scope to <500K).

## Decision

Use **pgvector** as a PostgreSQL extension in the existing database, with HNSW indexes for approximate nearest neighbor search.

Document chunks are stored in a `document_chunks` table alongside their embeddings, with `tenant_id` for isolation and standard SQL columns for metadata filtering.

## Consequences

### Positive

- One fewer service to deploy, monitor, and back up
- ACID consistency: document upload + embedding insert in a single transaction
- Rich metadata filtering via standard SQL (date ranges, categories, tags)
- Tenant isolation via existing RLS policies
- Familiar tooling (psql, pg_dump, Alembic migrations)

### Negative

- pgvector HNSW index build is slower than Qdrant's optimized engine
- At >1M vectors per query scope, latency may exceed Qdrant's
- Less specialized tuning knobs compared to a dedicated vector database

### Neutral

- Migration to Qdrant is straightforward if performance needs change: export embeddings, point search queries to Qdrant API
- pgvector 0.7+ supports HNSW with reasonable defaults (m=16, ef_construction=64)
