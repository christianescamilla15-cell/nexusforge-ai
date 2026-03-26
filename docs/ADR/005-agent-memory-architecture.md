# ADR-005: Three-Tier Agent Memory Architecture

## Status

Accepted

## Context

Agents in NexusForge need contextual memory to operate effectively across multi-step workflows and repeat interactions. Different types of memory have fundamentally different access patterns, lifetimes, and storage requirements:

- **Immediate context**: current execution state, intermediate results (millisecond access, per-execution lifetime)
- **Recent history**: past execution outcomes, conversation history (sub-second access, hours-to-days lifetime)
- **Long-term knowledge**: learned patterns, indexed documents, semantic associations (sub-second search, indefinite lifetime)

A single storage backend cannot optimally serve all three patterns.

## Decision

Implement a **3-tier memory architecture**:

### Tier 1: Working Memory (In-Process)

- **Storage**: Python dictionary held in the agent's execution context
- **Lifetime**: Single execution (destroyed when the run completes or the process restarts)
- **Access**: Direct object reference, nanosecond latency
- **Contents**: Current step inputs/outputs, scratch variables, chain-of-thought state

### Tier 2: Episodic Memory (Redis)

- **Storage**: Redis hashes and sorted sets with TTL
- **Lifetime**: Configurable TTL (default 24 hours, max 7 days)
- **Access**: Network call, sub-millisecond latency
- **Contents**: Recent execution summaries, conversation turns, agent observations
- **Key schema**: `memory:episodic:{tenant_id}:{agent_type}:{session_id}`

### Tier 3: Semantic Memory (pgvector)

- **Storage**: PostgreSQL with pgvector embeddings
- **Lifetime**: Indefinite (managed by document lifecycle)
- **Access**: SQL query with HNSW index, ~10ms latency
- **Contents**: Document chunks, learned patterns, entity knowledge graph edges

### Memory Flow

```
Execution starts
  -> Working memory initialized from step input
  -> Agent queries episodic memory for recent context
  -> Agent queries semantic memory for relevant knowledge
  -> Agent processes and produces output
  -> Key observations written to episodic memory
  -> New knowledge indexed in semantic memory (if applicable)
  -> Working memory discarded
```

## Consequences

### Positive

- Each tier is optimized for its access pattern and lifecycle
- No single point of failure: working memory loss only affects the current execution
- Episodic memory TTL prevents unbounded growth
- Semantic memory benefits from pgvector's ACID guarantees and SQL filtering

### Negative

- Three storage systems to understand and maintain (though Redis and PostgreSQL are already in the stack)
- Memory promotion logic (episodic -> semantic) adds complexity
- Cache invalidation across tiers requires careful handling

### Neutral

- Working memory size is bounded by process memory; very large intermediate results should be stored in object storage and referenced by pointer
- Episodic memory TTL is configurable per agent type (some agents benefit from longer recall)
- Semantic memory embeddings use the same model as document RAG for consistency
