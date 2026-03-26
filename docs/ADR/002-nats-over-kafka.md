# ADR-002: Redis Pub/Sub Over NATS or Kafka for Event Bus

## Status

Accepted

## Context

The orchestration engine needs asynchronous messaging for several purposes:

- **Step completion events**: when an agent finishes a step, downstream steps must be notified
- **Task queuing**: long-running agent executions should be queued and processed by workers
- **Real-time updates**: clients polling or subscribing to run status changes

Options evaluated:

| Criteria | Kafka | NATS | Redis Pub/Sub + Streams |
|---|---|---|---|
| Operational complexity | High (ZooKeeper/KRaft, partitions) | Medium (clustered NATS) | Low (already in stack) |
| Durability | Excellent | Good (JetStream) | Good (Streams with AOF) |
| Throughput | Very high | High | Sufficient (<10k msg/s) |
| New infrastructure | Yes | Yes | No |
| Team familiarity | Low | Low | High |

## Decision

Use **Redis Pub/Sub** for fire-and-forget event notifications (step status changes, real-time updates) and **Redis Streams** for durable task queuing (agent execution jobs that must not be lost).

Redis is already in the stack as the episodic memory tier and caching layer, so this adds no new infrastructure dependency.

## Consequences

### Positive

- Zero additional infrastructure: Redis is already deployed and operated
- Redis Streams provide consumer groups with acknowledgment, sufficient for task queue needs
- Simple client libraries (aioredis) already in use
- Low latency for pub/sub notifications

### Negative

- Redis Pub/Sub is fire-and-forget; messages are lost if no subscriber is listening (acceptable for status updates, not for task queuing)
- Redis Streams lack Kafka's partitioning model; horizontal scaling is limited to consumer groups
- If message volume exceeds ~10k/s, will need to revisit

### Neutral

- Migration path to NATS JetStream or Kafka exists if scale demands it
- Redis Streams consumer groups map well to our worker pool model
