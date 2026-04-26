# Internal Security Retro -- NexusForge AI (2026-04-25)

**Auditor**: Claude Opus 4.7 + Security Auditor agent + Explore agent (architectural map)
**Date**: 2026-04-25
**HEAD at retro time**: `6c738eb` (post F-01 + F-02 + Ruta B validators)
**Scope**: 7 areas not covered by [2026-04-16 Opus 4.6 audit](2026-04-16-opus46-independent.md): auth lifecycle, multi-tenant isolation, LLM-specific risks, refactor engine subprocess surface, Stripe billing, deploy/ops security, dependency / supply chain.

> **Methodology gap flagged for the prior audit**: F-01..F-11 was heavy on calibration / strangler logic and light on the request-handling perimeter. This retro fills that gap. Future audits should always include a tenant-isolation sweep + a webhook-handler sweep.

---

## 1. Attack-surface diagnostic (summary)

| Layer | Endpoints | Auth | Dominant risk |
|---|---|---|---|
| Public (no JWT) | 8 | n/a | OAuth replay, webhook spoof, prefix collision |
| JWT-required | 40+ | HS256, 8h, no refresh, no revocation | Stolen JWT lives 8h; cannot be revoked |
| Mythos (X-Mythos-Key) | 9 categories | HMAC of `JWT_SECRET` | `/mythos/key` leakable via X-Forwarded-For |
| Stripe webhook | 1 | Signature + shared secret | Accepts any event when `STRIPE_SECRET` empty |
| Refactor engine | 6 | JWT + rate-limit | SSRF via arbitrary git clone |
| Agent tools | 6 (`capabilities.py`) | Indirect via agents | `run_code` runs `python -c` unsandboxed |

**Critical SPOF**: `JWT_SECRET` is the master key for everything -- JWT signing, Mythos key derivation, Fernet API-key encryption. Rotating it bricks every encrypted API key in the DB. **No rotation runbook exists.**

---

## 2. Findings (verified)

### CRITICAL (5 -- all manually confirmed by file:line read)

#### C-1 -- Cross-tenant workflow theft
**File**: `backend/app/routes/automations.py:42-46`, `:200-202`

`_launch_run` and `publish_automation` look up workflows by `id` only:

```sql
SELECT dag_definition FROM workflows WHERE id = $1   -- missing AND user_id
```

**Attack**: any logged-in user enumerates UUIDs (or grabs them from logs/traces), publishes an automation pointing at the victim's `workflow_id`, runs it -- the victim's DAG executes and outputs flow to the attacker's `output_config`.

**Fix**: add `AND user_id = $2::uuid` and propagate `user_id` through the call signature. CI grep gate to prevent regression.

#### C-2 -- `OR user_id IS NULL` lets any logged-in user read any orphan run
**File**: `backend/app/routes/executions_db.py:59`, `:81`, `:109`, `:138`

All 4 read endpoints (`get_execution`, `/steps`, `/events`, `/timeline`):

```sql
WHERE id = $1 AND (user_id = $2::uuid OR user_id IS NULL)
```

Background scheduler runs, webhook-triggered runs, and runs where `_launch_run` failed to coerce the UUID (line 60: `uid = None`) all land with `user_id = NULL` -- world-readable to every account.

**Attack**: enumerate run UUIDs (or grab from logs/OpenTelemetry), read outputs/events/steps of webhook automations belonging to other tenants -- includes LLM outputs, scraped URLs, dispatch metadata.

**Fix**: drop `OR user_id IS NULL`; backfill orphans with synthetic system user_id. Add CI grep gate.

#### C-3 -- SSRF + arbitrary-host git clone via authenticated /refactor/ingest
**File**: `backend/app/refactor/ingestion.py:272-273`, `:508-520`

```python
if path.startswith("http") or path.startswith("git@"):
    subprocess.run(["git", "clone", path, ...])  # path is attacker-controlled
```

**Attack**: free-tier user POSTs `{"path": "http://169.254.169.254/latest/meta-data"}` (Render metadata) or `{"path": "git@github.com:victim/private.git"}` -- if the container has cached deploy keys / `~/.gitconfig`, the clone succeeds and the content flows through scanner output to the response.

**Fix**: (a) host allowlist (`github.com`, `gitlab.com`); (b) `env={"GIT_TERMINAL_PROMPT": "0", "HOME": "/tmp/empty", "GIT_CONFIG_GLOBAL": "/dev/null"}`; (c) reject `git@` and `ssh://`; (d) gate behind paid plan or admin role.

#### C-4 -- Unsandboxed RCE via `run_code` agent tool
**File**: `backend/app/agents/capabilities.py:68-87`

```python
proc = await asyncio.create_subprocess_exec("python", "-c", code, ...)
```

No sandbox, no env stripping, 10s timeout (more than enough for `os.environ['JWT_SECRET']` + httpx exfil).

**Attack**: prompt injection via `/api/wizard/chat` makes an agent emit `tool_use(run_code)` with code that reads env vars and POSTs them to attacker.

**Fix**: feature flag `ALLOW_CODE_EXEC=false` default-off + AST allowlist when on. If kept long-term: nsjail/firejail with read-only FS, no network, 64 MB cap, scrubbed `os.environ`.

#### C-5 -- Stripe webhook accepts everything when `STRIPE_SECRET` empty
**File**: `backend/app/auth/billing.py:111-149`

```python
if not STRIPE_SECRET:
    return {"received": True}   # accepts any body as OK
```

Plus: no idempotency on `event["id"]`; `org_id` taken from metadata without re-fetching from Stripe.

**Attacks**: (a) misconfigured deploy → endpoint accepts spoofed events silently; (b) replay `checkout.session.completed` → free upgrade to enterprise; (c) user A passes B's `org_id` in checkout metadata → upgrade B's plan with A's payment.

**Fix**: fail-startup if `STRIPE_SECRET_KEY` set but `STRIPE_WEBHOOK_SECRET` missing; re-fetch session via `stripe.checkout.Session.retrieve(session.id)`; `processed_stripe_events` table with `PRIMARY KEY (event_id)` for idempotency; verify `org_id` belongs to `user_id`.

### HIGH (6)

| ID | File | Summary | Effort |
|---|---|---|---|
| H-1 | `auth/oauth.py:18-46` | Google OAuth uses deprecated `tokeninfo` endpoint, no nonce → replay attack | 2h |
| H-2 | `auth/jwt_handler.py:7-21` + `auth/encryption.py:17-20` | JWT 8h sin refresh / sin `jti` / sin revocación. Y rotar `JWT_SECRET` brickea Fernet | 1-2 días |
| H-3 | `security/routes.py:162-173` | `/api/mythos/key` leakable via `X-Forwarded-For: 127.0.0.1` if Uvicorn trusts proxy headers | 30 min |
| H-4 | `auth/middleware.py:21-28` | `PUBLIC_PREFIXES` uses `path.startswith()` → future `/api/refactor/showcase-debug` silently public | 1h |
| H-5 | `main.py:189` + `render.yaml:28` | CORS allowlist has stale `frontend-silk-three-66.vercel.app`; `allow_methods=*`, `allow_headers=*` | 30 min |
| H-6 | `routes/wizard_chat.py:96-98`, `:121`, `:169` | `OLLAMA_TUNNEL_URL` SSRF pivot if combined with C-4 RCE; Ollama default no-auth | 1h |

### MEDIUM (10)

- **M-1** Streaming chat leak: `str(e)` in error path leaks internal URLs (`wizard_chat.py:155, 215, 295, 343, 504`).
- **M-2** Password min 6 chars + login on PUBLIC_PREFIX (no per-IP rate limit) → credential stuffing wide open.
- **M-3** `routes/refactor.py:120, 129` -- `_jobs: dict[str, dict]` global keyed by `project_path` (not `user_id`). Cross-tenant collision.
- **M-4** `refactor/pr_generator.py:49, 56, 73, 123-130` -- `git checkout -b` in process cwd; if `project_path` is the backend repo, dirties server git state.
- **M-5** `security/routes.py:89` -- `report = scanner.full_scan` (missing `()`); dead code suggesting category_scan tests miss the spec.
- **M-6** `requirements.txt` -- floating pins on `cryptography`, `sentry-sdk`, `bcrypt`, `motor`, `crawl4ai`. A breaking 5.x of `cryptography` brick Fernet decrypt.
- **M-7** `/openapi.json` in DEBUG enumerates `/api/mythos/*` and `/api/admin/*`. Missing `include_in_schema=False`.
- **M-8** Episodic memory MongoDB lacks `org_id` filtering visible -- cross-tenant recall risk.
- **M-9** No key rotation runbook (architectural).
- **M-10** No per-tenant Fernet key -- DB dump = total cross-tenant compromise.

### LOW (4)

- **L-1** `auth/encryption.py:17-20` -- `_KEY = jwt_secret.encode()[:32]` truncates UTF-8 mid-character (sloppy, not a vuln).
- **L-2** `auth/billing.py:144-148` -- org `plan` upgrade trusts metadata `org_id` (post-signature, but no ownership check).
- **L-3** `memory/anthropic_memory_tool.py:268-274` -- prompt-injection regex is allowlist-of-known-strings, trivially bypassable.
- **L-4** `auth/codes.py:14` -- 6-digit reset code, 15min TTL, no per-email rate limit on `verify_code` → 100 req/s × 15min covers all 900k codes.

---

## 3. Architectural / process risks

- **A-01** No key rotation runbook. `JWT_SECRET` derives JWT signing + Mythos HMAC + Fernet AES key. Rotating bricks everything.
- **A-02** No DB-layer tenant isolation primitive (no RLS, no `_with_tenant` helper, no CI gate).
- **A-03** No secret-rotation audit log (who/when/which version of `JWT_SECRET`).
- **A-04** No per-tenant Fernet key (single global key encrypts all stored API keys).
- **A-05** No content-egress audit on agent tools (`read_file`, `web_scrape`, `run_code` send arbitrary local content into LLM provider calls).
- **A-06** Mythos's own `_SECRET_IGNORE_PATTERNS` excludes its own file but not its baselines; injection-pattern set lacks symmetric self-exclusions.
- **A-07** Vercel rewrite `/((?!assets/).*) → /index.html` allows phishing-friendly URLs (`/login.microsoft.com.fakebank.com` returns the React app).

---

## 4. Prioritized implementation plan

### Sprint 1 -- immediate (1-2 days, real blockers)

| # | Action | Effort | Why first |
|---|---|---|---|
| 1 | C-1 + C-2 (tenant isolation in automations + executions) | 4-6h | Largest blast radius. Prior audit didn't touch this. CI grep gate makes it self-enforcing. |
| 2 | C-5 (Stripe hardening: fail-startup + re-fetch + idempotency) | 3-4h | Billing fraud is direct money loss. Mechanical fix. |
| 3 | H-3 (delete `/mythos/key` endpoint) | 30 min | Reduces surface without losing functionality (use `render exec`). |

### Sprint 2 -- next (3-5 days, RCE/SSRF/auth-bypass)

| # | Action | Effort |
|---|---|---|
| 4 | C-3 + C-4 (refactor SSRF allowlist + `run_code` flag-off) | 6-8h |
| 5 | H-1 + H-2 (real Google OAuth via `google-auth` + JWT secret split + refresh tokens) | 2-3 days |
| 6 | H-4 + H-5 (PUBLIC_PREFIXES regex + CORS allowlist cleanup) | 2h |

### Sprint 3 -- hardening (1 week, defense in depth + tech debt)

| # | Action | Effort |
|---|---|---|
| 7 | F-03 + F-04 + F-05 (rest of prior audit's HIGH findings) | 1 day |
| 8 | M-1 + M-2 + M-7 (sanitize error leaks + 12-char password + per-IP rate limit + `include_in_schema=False`) | 4h |
| 9 | M-6 (pin upper bounds + add `pip-audit` to CI) | 2h |
| 10 | A-01 + M-9 (key rotation runbook + `MultiFernet` for rotable Fernet) | 1-2 days |

### Platform work (separate, lower priority)

- M-8 (audit MongoDB episodic memory for `org_id` filtering)
- M-10 (per-tenant Fernet via `HKDF(global_secret, salt=tenant_id, info="api-keys")`)
- A-05 (DLP / audit log on content leaving the perimeter via LLM tools)

---

## 5. CI gates to add (process-level fixes)

1. `rg "WHERE id = \\\$1[^)]*\\)" backend/app/routes | grep -v "user_id\|org_id"` must be empty.
2. Every `@router.post(...)` receiving an external payload must verify a signature AND have idempotency.
3. Every app boot logs `JWT_SECRET fingerprint = sha256(secret)[:16]` so rotations are visible in request logs.
4. `pip-audit` runs in CI and fails on HIGH/CRITICAL CVEs.
5. `rg "OR user_id IS NULL" backend/` must be empty.

---

## 6. Executive summary

- **5 CRITICAL** verified by file:line read: cross-tenant data theft x2, SSRF, RCE remote, Stripe billing fraud.
- **6 HIGH**: OAuth replay, JWT no-refresh + no-rotation, Mythos key leak via proxy, prefix-collision auth bypass, CORS stale, Ollama tunnel pivot.
- **10 MEDIUM**: from requirements pinning to per-tenant Fernet absence.
- **4 LOW**: implementation cleanups + code-leak edge cases.
- **9 still open** from the 2026-04-16 audit (F-03..F-08 + F-09..F-11).

**Single biggest SPOF**: `JWT_SECRET` derives all crypto. No runbook = it cannot be rotated.

**One-day version of this plan**: C-1 + C-2 + C-5 + H-3 = 4 commits, ~10h work, closes the highest-impact demonstrable risks.
