# ADR-004: Row-Level Security for Multi-Tenant Isolation

## Status

Accepted

## Context

NexusForge must support multiple tenants (organizations) sharing the same deployment. Tenant data must be fully isolated -- no tenant should ever see another tenant's workflows, documents, or execution results.

Common strategies:

| Strategy | Isolation | Complexity | Cost |
|---|---|---|---|
| Separate databases per tenant | Strongest | High (connection pooling, migrations) | High |
| Separate schemas per tenant | Strong | Medium (dynamic schema management) | Medium |
| Shared schema + tenant_id column + RLS | Sufficient | Low | Low |

Our projected tenant count is <50 in year one. Operational simplicity and cost efficiency are priorities.

## Decision

Use a **shared database with a `tenant_id` column** on every tenant-scoped table, enforced by **PostgreSQL Row-Level Security (RLS)** policies.

Implementation approach:

1. Every tenant-scoped table includes a `tenant_id UUID NOT NULL` column
2. RLS policies enforce `tenant_id = current_setting('app.current_tenant_id')::uuid`
3. The API middleware sets `app.current_tenant_id` on every database session via `SET LOCAL`
4. A composite index on `(tenant_id, ...)` is added to frequently queried tables
5. Application-level checks serve as a second layer of defense

## Consequences

### Positive

- Single database to manage: one connection pool, one backup schedule, one migration path
- RLS enforcement is transparent to application code once configured
- Cost-effective: no per-tenant database provisioning
- Simple Alembic migrations: one schema, run once

### Negative

- RLS adds a small query planning overhead (negligible in practice)
- A misconfigured session (missing `SET LOCAL`) could leak data; requires careful middleware testing
- Noisy neighbor risk: one tenant's heavy queries can affect others (mitigate with connection pool limits and query timeouts)

### Neutral

- If a tenant requires dedicated isolation (compliance, enterprise), we can extract them to a separate schema or database without changing the application code
- Monitoring should include per-tenant query metrics to detect noisy neighbors early
