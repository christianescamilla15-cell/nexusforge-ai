# NexusForge AI — Security Documentation

## Authentication

### JWT Tokens

User authentication uses short-lived JWT tokens issued by the Auth module.

- **Algorithm**: HS256 (symmetric) for single-instance; RS256 (asymmetric) for distributed deployments
- **Access token TTL**: 15 minutes
- **Refresh token TTL**: 7 days (stored in HTTP-only secure cookie)
- **Token payload**: `{ sub: user_id, tenant_id, role, exp, iat }`

### API Keys

For programmatic access (SDK, CI/CD integrations), tenants can create long-lived API keys.

- API keys are prefixed with `nxf_` for easy identification in logs
- Keys are stored as bcrypt hashes in the database; the plaintext is shown only once at creation
- Each key is scoped to a tenant and has an associated role
- Keys can be revoked instantly via the API or admin UI
- Rate limits apply per API key independently

### Authentication flow

```
Client -> POST /api/auth/login { email, password }
       <- 200 { access_token, refresh_token (cookie) }

Client -> GET /api/workflows (Authorization: Bearer <access_token>)
       <- 200 [...]

Client -> POST /api/auth/refresh (cookie: refresh_token)
       <- 200 { access_token }
```

---

## Authorization (RBAC)

Four roles with hierarchical permissions:

| Permission | Owner | Admin | Member | Viewer |
|---|---|---|---|---|
| Manage tenant settings | Yes | No | No | No |
| Manage users & API keys | Yes | Yes | No | No |
| Create/edit workflows | Yes | Yes | Yes | No |
| Run workflows | Yes | Yes | Yes | No |
| View workflows & runs | Yes | Yes | Yes | Yes |
| View documents | Yes | Yes | Yes | Yes |
| Upload documents | Yes | Yes | Yes | No |
| Delete documents | Yes | Yes | No | No |

Role assignment:
- The user who creates a tenant is automatically assigned the **Owner** role
- Owners and Admins can invite users and assign roles
- Role changes are audit-logged

---

## Tenant Isolation

- Every database table with tenant-scoped data includes a `tenant_id` column
- PostgreSQL Row-Level Security (RLS) policies enforce isolation at the database level
- The API middleware sets `app.current_tenant_id` via `SET LOCAL` on every database session
- Redis keys are namespaced by tenant: `{tenant_id}:memory:...`
- API keys are bound to a single tenant
- Cross-tenant requests are rejected at the middleware layer before reaching business logic

---

## PII Detection and Redaction

Agents processing documents may encounter personally identifiable information. NexusForge includes a PII detection layer:

- **Detection**: Regex patterns and NER models identify common PII types (email, phone, SSN, credit card, names)
- **Redaction modes**:
  - `mask` — replace with `[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, etc.
  - `hash` — replace with a deterministic hash (allows deduplication without exposing PII)
  - `none` — pass through (for tenants who handle PII themselves)
- **Configuration**: per-tenant setting in tenant preferences
- **Logging**: PII is never written to application logs; log output runs through the same redaction pipeline

---

## Secret Management

- **Environment variables**: all secrets (API keys, database credentials, JWT signing keys) are injected via environment variables
- **Never in code**: secrets are excluded from version control via `.gitignore` and pre-commit hooks
- **Production**: secrets are managed via Kubernetes Secrets (encrypted at rest with etcd encryption) or a dedicated secrets manager (HashiCorp Vault, AWS Secrets Manager)
- **Rotation**: API keys can be rotated without downtime; JWT signing keys support key-pair rotation with a grace period for the old key
- **.env.example**: contains placeholder values documenting all required variables without exposing real credentials

---

## Rate Limiting

Rate limits protect against abuse and ensure fair resource allocation across tenants.

| Scope | Default Limit | Configurable |
|---|---|---|
| API requests per tenant | 60/min | Yes (per-tenant override) |
| Workflow runs per tenant | 100/hour | Yes |
| Document uploads per tenant | 50/hour | Yes |
| LLM tokens per tenant | 100,000/hour | Yes |

Implementation:
- Redis-based sliding window counter
- Rate limit headers included in every response: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- 429 Too Many Requests response with `Retry-After` header when exceeded

---

## CORS Configuration

- `ALLOWED_ORIGINS` environment variable accepts a comma-separated list of origins
- Default (development): `http://localhost:3000`
- Production: explicitly list allowed frontend domains
- Credentials (`Access-Control-Allow-Credentials`) enabled for cookie-based refresh tokens
- Methods: `GET, POST, PATCH, DELETE, OPTIONS`
- Headers: `Authorization, Content-Type, X-Request-ID`
- Preflight cache: 600 seconds

---

## Additional Security Measures

### Input validation
- All API inputs validated with Pydantic models
- Maximum request body size: 10MB (configurable)
- SQL injection prevented by SQLAlchemy parameterized queries
- XSS prevented by JSON-only API responses (no HTML rendering)

### Audit logging
- Authentication events (login, logout, failed attempts)
- Role changes and user invitations
- API key creation and revocation
- Workflow creation and deletion
- Sensitive configuration changes

### Dependency security
- Automated dependency scanning via Dependabot / Snyk
- Docker images built from minimal base images (python:3.11-slim)
- Container runs as non-root user
- Read-only filesystem where possible
