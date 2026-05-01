"""Feature-driven addon files.

Each template's `_render_*` function emits its baseline file tree
and then calls `apply_addons(files, spec, template_id)` here. We
inspect `spec.features`, `spec.integrations`, and `spec.description`
for known signals (slack, stripe, openai/anthropic, redis, email,
docker) and append/inject the right files.

Why this module exists separately from `templates.py`:
  - Keeps each template's render function focused on the canonical
    skeleton; this layer adds variation.
  - One place to extend when a new integration becomes common — e.g.
    adding Sentry doesn't require touching all 7 templates.
  - Idempotent: every addon checks for the target file before
    writing, so a template that already provides (say) a Dockerfile
    is never overwritten.

Detection is lossy on purpose: the LLM extractor often puts the
same intent in different slots ("slack" might be in features or
integrations). We OR all three text sources together.
"""
from __future__ import annotations

from .schemas import PlatformSpec


# ── detection ───────────────────────────────────────────────────────


_INTEGRATION_CATALOGUE: dict[str, tuple[str, ...]] = {
    "slack": ("slack",),
    "stripe": ("stripe",),
    "ai": ("openai", "anthropic", "claude", "llm", "gpt", "gemini"),
    "redis": ("redis", "upstash"),
    "email": ("sendgrid", "postmark", "resend", "mailgun", "smtp", "transactional email"),
    "docker": ("docker",),
}


def _detect(spec: PlatformSpec) -> set[str]:
    """Return the canonical set of integration tags present in the
    spec. Matches against features, integrations, and the free-form
    description string (case-insensitive substring)."""
    haystack = " ".join(
        [(spec.description or "").lower()]
        + [s.lower() for s in spec.features]
        + [s.lower() for s in spec.integrations]
    )
    detected: set[str] = set()
    for tag, terms in _INTEGRATION_CATALOGUE.items():
        if any(term in haystack for term in terms):
            detected.add(tag)
    return detected


# ── INTEGRATIONS.md ─────────────────────────────────────────────────


def _slack_section() -> str:
    return """## Slack notifications

Set `SLACK_WEBHOOK_URL` in your env (Slack workspace → Apps → Incoming Webhooks).

Quick smoke test:

```bash
curl -X POST -H 'Content-Type: application/json' \\
  -d '{"text":"Hello from your new app"}' \\
  "$SLACK_WEBHOOK_URL"
```

Wire it from your code: POST a JSON `{"text": "..."}` payload to that URL
on whichever event you want to broadcast (deploy, error, signup, etc.).
Treat the URL as a secret — never ship it in client code."""


def _stripe_section() -> str:
    return """## Stripe payments

Required env vars:
- `STRIPE_SECRET_KEY` — start with `sk_test_...` until you go live
- `STRIPE_WEBHOOK_SECRET` — copied from Dashboard → Webhooks endpoint

Critical security rule: **always verify** the `Stripe-Signature` header on
incoming webhook requests with `stripe.webhooks.constructEvent` (or your
language's equivalent) before trusting the payload. An unverified webhook
is a public mutation endpoint.

Local testing: install the Stripe CLI and run
`stripe listen --forward-to localhost:PORT/webhook` to forward real test
events to your dev server."""


def _ai_section() -> str:
    return """## AI provider (OpenAI / Anthropic)

Set whichever key applies:
- `OPENAI_API_KEY=sk-...`
- `ANTHROPIC_API_KEY=sk-ant-...`

Routing rule: **never** call AI APIs directly from client-side code.
Route through your backend. The client should only see your own endpoints,
which add auth + rate limiting + key rotation in one place.

For high-volume async workloads, consider a queue (Redis/BullMQ/Celery) so
slow LLM calls don't tie up your request workers."""


def _redis_section() -> str:
    return """## Redis cache / queue

Set `REDIS_URL` — e.g., `redis://localhost:6379` for local, or
`rediss://default:PASSWORD@host:6379` for managed (Upstash, Render Redis,
Elasticache). Note the double `s` for TLS.

Common uses: response caching (TTL'd JSON), rate limiting (per-IP token
bucket), background job queue, websocket session store, ephemeral idempotency
keys for webhooks."""


def _email_section() -> str:
    return """## Transactional email

Pick one provider — they all expose a similar HTTP API:
- SendGrid (`SENDGRID_API_KEY`)
- Postmark (`POSTMARK_API_TOKEN`)
- Resend (`RESEND_API_KEY`)
- Mailgun (`MAILGUN_API_KEY`)
- Or raw SMTP (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`)

Set up SPF/DKIM/DMARC for your sending domain before you launch. Without
those records most providers will dump you in spam regardless of what
your code does."""


_SECTIONS: dict[str, str] = {
    "slack": _slack_section(),
    "stripe": _stripe_section(),
    "ai": _ai_section(),
    "redis": _redis_section(),
    "email": _email_section(),
}


def _build_integrations_md(detected: set[str]) -> str:
    """Build INTEGRATIONS.md from detected integrations. `docker` is
    excluded because it gets its own files (Dockerfile + compose),
    not a docs section."""
    relevant = sorted(detected & set(_SECTIONS.keys()))
    if not relevant:
        return ""
    parts = [
        "# Integration wireup",
        "",
        "The synthesizer detected these integrations from your spec. Each "
        "section below has the env vars + the wireup pattern for it.",
        "",
    ]
    for tag in relevant:
        parts.append(_SECTIONS[tag])
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


# ── Docker ──────────────────────────────────────────────────────────


_DOCKERFILES: dict[str, str] = {
    "fastapi_react_postgres": """# Backend service. Builds the Python app; the frontend is built
# separately into static files and served behind a CDN/proxy.
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    "express_next_postgres": """# Backend Express API.
FROM node:20-alpine

WORKDIR /app

COPY backend/package.json ./
RUN npm install --omit=dev

COPY backend/ ./
RUN npm run build

EXPOSE 8000
CMD ["node", "dist/index.js"]
""",
    "django_postgres": """FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "PROJECT_MODULE.wsgi:application"]
""",
    "go_gin_postgres": """# Multi-stage build: compile a static binary, then ship a tiny image.
FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /out/app .

FROM alpine:3.19
RUN apk add --no-cache ca-certificates
COPY --from=builder /out/app /app
EXPOSE 8000
ENTRYPOINT ["/app"]
""",
    "rails_postgres": """FROM ruby:3.2-slim

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY Gemfile ./
RUN bundle install

COPY . ./

EXPOSE 3000
CMD ["bin/rails", "s", "-b", "0.0.0.0", "-p", "3000"]
""",
    "phoenix_postgres": """FROM elixir:1.16-alpine AS builder

RUN apk add --no-cache build-base git

WORKDIR /app

ENV MIX_ENV=prod
COPY mix.exs ./
RUN mix local.hex --force && mix local.rebar --force && \\
    mix deps.get --only prod && mix deps.compile

COPY config ./config
COPY lib ./lib
COPY priv ./priv

RUN mix compile && mix release

FROM alpine:3.19
RUN apk add --no-cache libstdc++ openssl ncurses-libs
WORKDIR /app
COPY --from=builder /app/_build/prod/rel ./rel

EXPOSE 4000
ENV PORT=4000
CMD ["sh", "-c", "rel/*/bin/* start"]
""",
    "spring_boot_postgres": """# Multi-stage: Gradle build → tiny runtime.
FROM gradle:8.7-jdk21 AS builder
WORKDIR /src
COPY build.gradle.kts settings.gradle.kts gradle.properties ./
COPY src ./src
RUN gradle bootJar --no-daemon

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=builder /src/build/libs/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
""",
}


# (template_id, app_service_yaml, app_port). Compose inlines these
# as the `app` service; postgres is identical across all stacks.
_COMPOSE_PORTS: dict[str, int] = {
    "fastapi_react_postgres": 8000,
    "express_next_postgres": 8000,
    "django_postgres": 8000,
    "go_gin_postgres": 8000,
    "rails_postgres": 3000,
    "phoenix_postgres": 4000,
    "spring_boot_postgres": 8080,
}


def _build_dockerfile(template_id: str, spec: PlatformSpec) -> str:
    raw = _DOCKERFILES[template_id]
    if template_id == "django_postgres":
        # Substitute the project module path so gunicorn loads the
        # right WSGI app. Use the snake-cased project name (same as
        # the Django render).
        snake = (spec.project_name or "app").lower()
        snake = "".join(c if c.isalnum() or c == "_" else "_" for c in snake.replace("-", "_"))
        raw = raw.replace("PROJECT_MODULE", snake)
    return raw


def _build_compose(template_id: str, spec: PlatformSpec, detected: set[str]) -> str:
    port = _COMPOSE_PORTS.get(template_id, 8000)
    redis_block = ""
    if "redis" in detected:
        redis_block = """
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
"""

    redis_url_env = "      REDIS_URL: redis://redis:6379\n" if "redis" in detected else ""
    db_url_format = "postgres://app:app@db:5432/app"
    if template_id == "spring_boot_postgres":
        # Spring Boot wants jdbc-style URLs.
        spring_env = (
            "      SPRING_DATASOURCE_URL: jdbc:postgresql://db:5432/app\n"
            "      SPRING_DATASOURCE_USERNAME: app\n"
            "      SPRING_DATASOURCE_PASSWORD: app\n"
        )
        db_env = spring_env
    else:
        db_env = f"      DATABASE_URL: {db_url_format}\n"

    return f"""# Generated by NexusForge Platform Synthesizer.
# Local development stack: app + postgres{(' + redis' if 'redis' in detected else '')}.
# Run with: docker compose up --build
services:
  app:
    build: .
    ports:
      - "{port}:{port}"
    environment:
{db_env}{redis_url_env}    depends_on:
      - db

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
{redis_block}
volumes:
  pgdata:
"""


# ── public entry ────────────────────────────────────────────────────


def apply_addons(files: dict[str, str], spec: PlatformSpec, template_id: str) -> set[str]:
    """Mutate `files` to add integration addons.

    Returns the set of detected integration tags so the caller can
    surface them in the build result (next_steps, warnings).

    Idempotent: never overwrites a key that already exists in `files`.
    """
    detected = _detect(spec)
    if not detected:
        return detected

    md = _build_integrations_md(detected)
    if md and "INTEGRATIONS.md" not in files:
        files["INTEGRATIONS.md"] = md

    if "docker" in detected:
        if "Dockerfile" not in files and template_id in _DOCKERFILES:
            files["Dockerfile"] = _build_dockerfile(template_id, spec)
        if "docker-compose.yml" not in files and template_id in _COMPOSE_PORTS:
            files["docker-compose.yml"] = _build_compose(template_id, spec, detected)
        if ".dockerignore" not in files:
            files[".dockerignore"] = _DOCKERIGNORE

    return detected


_DOCKERIGNORE = """.git
.env
.env.local
node_modules
__pycache__
*.pyc
.venv
dist
build
out
target
_build
deps
.gradle
.idea
.vscode
"""
