# Design Decisions — NexusForge AI

## 1. DAG Execution Over Linear Chaining

**Decision:** Use a DAG (Directed Acyclic Graph) execution engine with Kahn's algorithm instead of sequential agent chains.

**Rationale:** Linear chains break when workflows require parallel branches, conditional steps, or complex dependency resolution. DAG execution enables:
- Topological ordering with dependency validation
- Parallel execution of independent agent tasks
- Checkpoint/resume at any node
- Retry policies per node without restarting the full chain

**Tradeoff:** Higher orchestration complexity. Requires a state machine and careful edge validation.

---

## 2. External Memory Over Long Prompts

**Decision:** Keep agents stateless. Memory lives in a 3-tier external system.

**Tiers:**
- **Working memory** (Redis) — fast, ephemeral, per-execution context
- **Episodic memory** (PostgreSQL) — persistent, queryable execution history
- **Semantic memory** (pgvector) — vector similarity for RAG retrieval

**Rationale:** Long prompts are fragile — they hit token limits, degrade quality, and can't be shared across agents. External memory decouples agent logic from context management.

**Tradeoff:** More infrastructure to manage. Requires careful consistency between tiers.

---

## 3. Multi-Provider LLM Routing

**Decision:** Groq (Llama 3.3 70B) as primary provider, Claude as fallback. Circuit breaker pattern for automatic failover.

**Rationale:** Single-provider dependency is a production risk. Groq is fast and free-tier friendly. Claude provides higher quality for complex reasoning. Circuit breaker prevents cascading failures.

**Tradeoff:** Response quality varies between providers. Prompts must be provider-agnostic.

---

## 4. Redis + PostgreSQL Split

**Decision:** Use Redis for hot state and PostgreSQL for durable state.

**Rationale:**
- Redis: agent working memory, pub/sub events, session state. Needs <10ms reads.
- PostgreSQL: episodic memory, RAG index (pgvector), execution logs. Needs durability and queries.

**Tradeoff:** Two data stores to maintain. Requires careful data lifecycle management.

---

## 5. Self-Healing with 5 Strategies

**Decision:** Implement 5 recovery strategies instead of a single retry loop.

**Strategies:**
1. Retry with exponential backoff
2. Provider failover (Groq → Claude)
3. Agent substitution (swap to backup agent)
4. Context reduction (trim memory, retry with less context)
5. Graceful degradation (return partial results)

**Rationale:** Different failure modes require different recovery strategies. Tool errors need retry. Provider outages need failover. Context overflow needs reduction.

**Tradeoff:** More code paths to test. Each strategy adds complexity to the healing module.
