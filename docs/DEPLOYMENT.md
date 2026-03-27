# NexusForge AI — Deployment Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Staging](#staging)
- [Production](#production)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Monitoring](#monitoring)

---

## Prerequisites

- Docker 24+ and Docker Compose v2
- Node.js 18+ (for SDK development)
- Python 3.11+ (for backend development)
- Terraform 1.5+ (for staging/production infrastructure)
- kubectl 1.28+ (for Kubernetes deployments)
- A PostgreSQL-compatible database with pgvector extension
- Redis 7+

---

## Local Development

### 1. Clone and configure

```bash
git clone https://github.com/your-org/nexusforge.git
cd nexusforge
cp .env.example .env
# Edit .env with your API keys (ANTHROPIC_API_KEY, etc.)
```

### 2. Start all services

```bash
docker compose up -d
```

This starts:
- **api** (FastAPI) on port 8000
- **postgres** (with pgvector) on port 5432
- **redis** on port 6379
- **worker** (background task processor)

### 3. Run database migrations

```bash
docker compose exec api alembic upgrade head
```

### 4. Verify

```bash
curl http://localhost:8000/api/health
# {"status":"ok","version":"0.1.0","services":{"postgres":"up","redis":"up"}}
```

### 5. Development workflow

```bash
# Backend (auto-reload)
docker compose up api --build

# SDK
cd packages/sdk
npm install
npm test

# Run all tests
docker compose exec api pytest tests/ -v
```

---

## Local Kubernetes (minikube / kind / Docker Desktop)

Deploy NexusForge to a local Kubernetes cluster for testing K8s manifests, networking, and production-like behavior without cloud infrastructure.

### Prerequisites

- Docker 24+
- kubectl 1.28+
- One of: minikube, kind, or Docker Desktop with Kubernetes enabled

### 1. Start your local cluster

```bash
# Option A: minikube
minikube start --cpus=4 --memory=4096

# Option B: kind
kind create cluster --name nexusforge

# Option C: Docker Desktop
# Enable Kubernetes in Docker Desktop settings
```

### 2. Deploy

```bash
./scripts/k8s-local-deploy.sh
```

This script will:
- Build Docker images locally
- Load images into the cluster (kind auto-loads)
- Create the `nexusforge` namespace
- Apply ConfigMaps and Secrets
- Deploy Redis, backend gateway, workers, and frontend

### 3. Access services via port-forward

```bash
# Backend API
kubectl -n nexusforge port-forward svc/gateway 8000:8000
# -> http://localhost:8000

# Frontend
kubectl -n nexusforge port-forward svc/frontend 3000:80
# -> http://localhost:3000

# Redis (for debugging)
kubectl -n nexusforge port-forward svc/redis 6379:6379
```

### 4. Health check

```bash
./scripts/k8s-health.sh

# Or manually:
curl http://localhost:8000/health
```

### 5. View logs

```bash
# Gateway logs
kubectl -n nexusforge logs -f deployment/gateway

# Worker logs
kubectl -n nexusforge logs -f deployment/worker

# All pods
kubectl -n nexusforge logs -f -l app.kubernetes.io/part-of=nexusforge
```

### 6. Teardown

```bash
./scripts/k8s-teardown.sh
```

This deletes the `nexusforge` namespace and all resources within it.

### Notes

- HPAs are skipped in local mode (no metrics-server by default)
- Secrets use placeholder values -- update `infrastructure/k8s/base/secrets.yml` with real API keys
- Resource limits are reduced for local (128Mi-256Mi memory, 100m-250m CPU)
- Replicas are set to 1 for all services to conserve resources

---

## Staging

Staging uses Terraform to provision cloud infrastructure and Kubernetes for orchestration.

### 1. Infrastructure provisioning

```bash
cd infra/terraform/staging

terraform init
terraform plan -var-file="staging.tfvars"
terraform apply -var-file="staging.tfvars"
```

This provisions:
- Managed PostgreSQL instance (with pgvector)
- Managed Redis instance
- Kubernetes cluster (3 nodes)
- Container registry
- Load balancer

### 2. Build and push images

```bash
# Authenticate to container registry
docker login registry.example.com

# Build and push
docker build -t registry.example.com/nexusforge/api:staging-$(git rev-parse --short HEAD) .
docker push registry.example.com/nexusforge/api:staging-$(git rev-parse --short HEAD)
```

### 3. Deploy to Kubernetes

```bash
cd k8s/overlays/staging

# Update image tag in kustomization.yaml
kustomize edit set image api=registry.example.com/nexusforge/api:staging-$(git rev-parse --short HEAD)

# Apply
kubectl apply -k .
```

### 4. Run migrations

```bash
kubectl exec -it deployment/api -- alembic upgrade head
```

### 5. Verify

```bash
curl https://staging.nexusforge.example.com/api/health
```

---

## Production

Production follows the same pattern as staging with additional safeguards.

### 1. Infrastructure

```bash
cd infra/terraform/production

terraform init
terraform plan -var-file="production.tfvars"
terraform apply -var-file="production.tfvars"
```

Production differences from staging:
- Multi-AZ PostgreSQL with read replicas
- Redis cluster mode enabled
- Kubernetes: 5+ nodes with auto-scaling
- WAF and DDoS protection enabled
- Automated backups with 30-day retention

### 2. Deploy

```bash
cd k8s/overlays/production

# Use a tagged release, not a commit hash
kustomize edit set image api=registry.example.com/nexusforge/api:v0.1.0

kubectl apply -k .
```

### 3. Rolling update strategy

Production uses a rolling deployment strategy:
- `maxSurge: 1` — at most 1 extra pod during rollout
- `maxUnavailable: 0` — zero downtime
- Readiness probe must pass before traffic is routed
- Rollback on failed health checks: `kubectl rollout undo deployment/api`

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `REDIS_URL` | Yes | — | Redis connection string |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key for agent LLM calls |
| `SECRET_KEY` | Yes | — | JWT signing secret (min 32 chars) |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | Comma-separated CORS origins |
| `LOG_LEVEL` | No | `info` | Logging level (debug, info, warning, error) |
| `WORKER_CONCURRENCY` | No | `4` | Number of concurrent background workers |
| `MAX_TOKENS_DEFAULT` | No | `2048` | Default max tokens for agent LLM calls |
| `EMBEDDING_MODEL` | No | `text-embedding-3-small` | Model for document embeddings |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | API requests per minute per tenant |
| `SENTRY_DSN` | No | — | Sentry error tracking DSN |
| `OTEL_EXPORTER_ENDPOINT` | No | — | OpenTelemetry collector endpoint |

---

## Database Migrations

Migrations are managed with Alembic.

### Create a new migration

```bash
# Auto-generate from model changes
docker compose exec api alembic revision --autogenerate -m "add swarm_results table"

# Manual migration
docker compose exec api alembic revision -m "add index on tenant_id"
```

### Apply migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade one step
alembic upgrade +1

# Downgrade one step
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

### Migration best practices

- Always review auto-generated migrations before applying
- Test migrations against a copy of production data in staging
- Never modify a migration that has already been applied in production
- Include both `upgrade()` and `downgrade()` functions
- Large data migrations should run as background tasks, not in Alembic

---

## Monitoring

### Health checks

- **Liveness**: `GET /api/health` — returns 200 if the process is alive
- **Readiness**: `GET /api/health/ready` — returns 200 if all dependencies (DB, Redis) are reachable

### Metrics (OpenTelemetry)

The API exports metrics to an OpenTelemetry collector when `OTEL_EXPORTER_ENDPOINT` is set:

- `http_request_duration_seconds` — request latency histogram
- `http_requests_total` — request count by method, path, status
- `agent_execution_duration_seconds` — per-agent-type execution time
- `workflow_runs_total` — workflow runs by status
- `redis_memory_usage_bytes` — episodic memory utilization

### Recommended dashboards

1. **API Overview**: request rate, error rate, p50/p95/p99 latency
2. **Agent Performance**: execution time by agent type, token usage, error rate
3. **Workflow Health**: runs by status, step failure rate, queue depth
4. **Infrastructure**: CPU, memory, disk, connection pool utilization

### Alerting rules

| Alert | Condition | Severity |
|---|---|---|
| High error rate | 5xx rate > 5% for 5 min | Critical |
| Slow responses | p95 latency > 5s for 10 min | Warning |
| Database connections exhausted | pool usage > 90% for 5 min | Critical |
| Redis memory high | usage > 80% of max | Warning |
| Worker queue backlog | queue depth > 1000 for 10 min | Warning |
