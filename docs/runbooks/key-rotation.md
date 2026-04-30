# Runbook -- key rotation (JWT signing / Mythos HMAC / Fernet)

**Owner**: Christian Hernandez
**Last updated**: 2026-04-30 (per-tenant Fernet migration script —
M-10 followup complete; rotation overlap is now end-to-end for both
global `fernet:` and per-tenant `tfernet:` rows)
**History**: created 2026-04-25 (A-01 / M-9 from
[2026-04-25 internal retro](../audits/2026-04-25-internal-retro.md));
H-2 Phases 1-4 (split secrets + MultiFernet overlap + global
migration script) shipped 2026-04-27

> **2026-04-27 update**: most of the original procedure (which
> required a stop-the-world re-encryption window) is now obsolete.
> The new flow uses MultiFernet overlap + an idempotent migration
> script and does NOT require maintenance downtime. See
> [Modern flow (H-2 Phases 1-4)](#modern-flow-h-2-phases-1-4).
> The legacy procedure stays at the bottom for deploys that have
> not yet adopted the dedicated env vars.

---

## Modern flow (H-2 Phases 1-4)

The current code reads each cryptographic surface from its own
dedicated env var and falls back to `JWT_SECRET` only when the
dedicated var is unset:

| Surface | Env var | What it does |
|---|---|---|
| JWT signing | `JWT_SIGNING_SECRET` | HS256 signing/verification of access tokens |
| Mythos owner key | `MYTHOS_HMAC_SECRET` | HMAC input for `_derive_mythos_key()` |
| Fernet (primary) | `FERNET_KEY` | Encrypts new rows in `nf_api_keys` |
| Fernet (secondary) | `FERNET_KEYS_OLD` | Decrypt-only overlap window during rotation |

Each can be rotated independently and -- crucially -- without
bricking any other surface. Boot logs emit a `sha256[:16]`
fingerprint per surface so an operator can verify a rotation took
effect by diffing across deploys.

### Rotate the JWT signing secret (no re-encryption needed)

1. Generate the new secret:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
2. Set `JWT_SIGNING_SECRET` to the new value on Render. Use the
   dashboard (per the project's "NEVER use PUT on /env-vars without
   ALL existing vars" rule).
3. Render auto-redeploys. Existing JWTs become invalid; users get
   401 on next request and re-login. **No data brick.**
4. Confirm via boot log: `secret fingerprint jwt_signing: <new>` —
   should differ from the previous deploy. The other three
   fingerprints (mythos / fernet) should remain unchanged.

### Rotate the Mythos HMAC secret

1. Generate as above.
2. Set `MYTHOS_HMAC_SECRET`. Render redeploys.
3. The previously-derived X-Mythos-Key value is now invalid. Re-
   derive from the running container:
   ```
   render exec <service> -- python -c \
     "from app.security.mythos import _derive_mythos_key; print(_derive_mythos_key())"
   ```
4. Update any tooling / scripts that hit `/api/mythos/*` with the
   new key.

### Rotate the Fernet key (zero-downtime overlap flow)

This is the dangerous one in the legacy flow because it bricks
`nf_api_keys` if done naively. The Phase 2 + Phase 4 work adds an
overlap window that makes it routine.

1. Generate K2:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. **Single deploy that sets both env vars at once**:
   - `FERNET_KEY=K2` (the new primary)
   - `FERNET_KEYS_OLD=<current-K1>` (the previous primary as
     decrypt-only secondary)

   Render redeploys. The handler now runs `MultiFernet([K2, K1])`.
   New writes use K2; old K1 ciphertexts continue to decrypt
   transparently.
3. Run the re-encryption migration. Two options — both call the
   same `run_rotation_pass` and are idempotent:

   **Preferred: admin HTTP endpoint** (works from any machine with
   admin credentials, no shell access required):
   ```bash
   curl -X POST https://nexusforge-api.onrender.com/admin/security/fernet-rotation/global \
        -H "Authorization: Bearer <admin-jwt>"
   ```
   Returns a JSON summary: `{"status": "complete", "migrated": N,
   "already_primary": M, "failed": 0, ...}`.

   **Alternative: CLI via render exec** (when the endpoint is
   unavailable or the deploy doesn't have an admin user yet):
   ```bash
   render exec <service> -- python -m backend.scripts.rotate_fernet_keys
   ```

   Both paths iterate `user_provider_keys`, decrypt every row with
   whichever key still works, re-encrypt with K2, write back. Skip
   per-tenant (`tfernet:`) and legacy XOR rows.
4. Verify the response / log shows `failed=0` and a re-run reports
   `migrated=0, already_primary=<all>`. If `failed > 0`, investigate
   those rows manually before continuing — DO NOT drop
   FERNET_KEYS_OLD yet.
5. Drop `FERNET_KEYS_OLD` from Render env. Next redeploy runs
   single-Fernet on K2; the rotation is complete.

### Refresh-token rotation (kill all sessions)

H-2 Phase 3 refresh tokens (`ENABLE_REFRESH_TOKENS=true` deploys)
can be revoked en masse without rotating any secret:

```python
# render exec <service> -- python -c "..."
import asyncio
from app.auth.refresh import revoke_all_for_user
asyncio.run(revoke_all_for_user("USER_UUID"))
```

For account compromise: call `revoke_all_for_user` for the affected
user_id; their next access token expires within 15 minutes (the
short-access TTL) and they cannot mint a new one without
re-authenticating.

For platform-wide forced re-login: there is no built-in "wipe all
refresh tokens." The closest equivalent is rotating
`JWT_SIGNING_SECRET` (kills all access tokens immediately) which
forces every user to re-authenticate within minutes; their
existing refresh tokens become orphaned and TTL out within 7 days.

### Per-tenant Fernet rotation (`tfernet:` rows, zero-downtime overlap flow)

`tfernet:`-prefixed ciphertexts are derived per tenant via
`HKDF(ikm=JWT_SECRET, salt=user_id, info="nexusforge-api-keys-v1")`.
The IKM is the master `JWT_SECRET`, so rotating it changes the
derivation for every tenant at once. The 2026-04-27 + 2026-04-30
work added a `TENANT_FERNET_IKM_OLD` overlap env var plus a
re-encryption script, mirroring the global Fernet flow.

**Important pre-step**: rotating `JWT_SECRET` only affects the
per-tenant IKM if the sibling surfaces are already on dedicated
env vars. Otherwise it ALSO rotates JWT signing, Mythos HMAC, and
the global Fernet primary fallback — set `JWT_SIGNING_SECRET`,
`MYTHOS_HMAC_SECRET`, and `FERNET_KEY` first (one redeploy each)
so `JWT_SECRET` stops being a master key and becomes ONLY the
per-tenant IKM seed.

1. Generate K2 (any high-entropy string ≥ 32 bytes works as IKM —
   HKDF will hash it):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
2. **Single deploy that sets both env vars at once**:
   - `JWT_SECRET=K2` (the new master IKM)
   - `TENANT_FERNET_IKM_OLD=<current-K1>` (the previous master,
     comma-separated if you've rotated through several)

   Render redeploys. The per-tenant handler now wraps each derived
   tenant Fernet in `MultiFernet([primary_K2, secondary_K1])`.
   New writes use K2; old K1 ciphertexts decrypt transparently
   under each tenant's salt.
3. Run the per-tenant migration. Two options — both idempotent:

   **Preferred: admin HTTP endpoint**:
   ```bash
   curl -X POST https://nexusforge-api.onrender.com/admin/security/fernet-rotation/tenant \
        -H "Authorization: Bearer <admin-jwt>"
   ```
   Returns a JSON summary: `{"status": "complete", "migrated": N,
   "already_primary": M, "no_user_id_skipped": 0, "failed": 0, ...}`.

   **Alternative: CLI via render exec**:
   ```bash
   render exec <service> -- python -m backend.scripts.rotate_tenant_fernet_keys
   ```

   Both paths iterate every `tfernet:` row in `user_provider_keys`,
   try the primary IKM first (no-op if already migrated), fall
   through to each secondary IKM on `InvalidToken`, re-encrypt
   under the primary IKM with the row's `user_id` as salt, and
   write back. Skip global `fernet:` rows (handled by the global
   migration) and bare-base64 legacy XOR rows.
4. Verify the response / log reports `failed=0` AND
   `no_user_id_skipped=0`. A re-run should then show `migrated=0,
   already_primary=<all>`. If either count is nonzero, investigate
   manually before continuing — DO NOT drop `TENANT_FERNET_IKM_OLD`
   yet.
5. Drop `TENANT_FERNET_IKM_OLD` from Render env. Next redeploy
   runs single-IKM per-tenant Fernet; the rotation is complete.

**What this does NOT cover**: rotating `JWT_SECRET` while it is
still the fallback for `FERNET_KEY` (no dedicated `FERNET_KEY` set)
will brick global `fernet:` rows. Run the global Fernet rotation
flow above first if your deploy hasn't yet set `FERNET_KEY`.

---

## Why this runbook exists

`JWT_SECRET` is the single master key for everything cryptographic in
NexusForge:

1. **JWT signing**  -- HS256 over `JWT_SECRET` issues every session
   token. See `backend/app/auth/jwt_handler.py:15`.
2. **Mythos owner key**  -- `_derive_mythos_key()` is `hmac_sha512(JWT_SECRET,
   <constant-salt>)`. See `backend/app/security/mythos.py`.
3. **Fernet API-key encryption**  -- `_KEY = sha256(JWT_SECRET[:32]).digest()`
   encrypts every row of `nf_api_keys`. See
   `backend/app/auth/encryption.py:17`.

This means: **rotating `JWT_SECRET` naively bricks every encrypted
API key in the database**. A user's Stripe / Anthropic / Groq /
Google integrations all become un-decryptable.

This runbook documents the *non-naive* rotation procedure.

---

## Pre-flight checklist (every rotation)

- [ ] Confirm the rotation reason in writing (incident ticket / leak
      suspicion / scheduled rotation / quarterly hygiene).
- [ ] Schedule a 30-minute maintenance window. Rotation is **not**
      zero-downtime today (the JWT_SECRET split work tracked under
      H-2 will eventually make it so).
- [ ] Confirm a recent DB backup exists.
- [ ] Identify the current `JWT_SECRET` fingerprint by reading
      Render env vars (or running `python -c "import os, hashlib;
      print(hashlib.sha256(os.environ['JWT_SECRET'].encode()).hexdigest()[:16])"`
      on the deployed container via `render exec`).

---

## Procedure (manual, supervised)

### Step 1 -- Generate the new secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Capture the output in a secure password manager. Treat it as
production credentials. **Never commit it.**

### Step 2 -- Re-encrypt `nf_api_keys` with the new Fernet key

The Fernet key is derived from `JWT_SECRET[:32]` so the new secret
yields a new Fernet key. Existing rows must be re-encrypted before
the new secret is rotated in. Pseudocode for the migration script
(write as a one-shot Python script in `backend/scripts/`):

```python
from cryptography.fernet import Fernet
import asyncpg, hashlib, base64, asyncio, os

OLD = os.environ["JWT_SECRET_OLD"]
NEW = os.environ["JWT_SECRET_NEW"]

old_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(OLD.encode()).digest()))
new_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(NEW.encode()).digest()))

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    rows = await conn.fetch("SELECT id, encrypted_value FROM nf_api_keys")
    for row in rows:
        cipher = row["encrypted_value"].removeprefix("fernet:").encode()
        plain = old_fernet.decrypt(cipher)
        new_cipher = "fernet:" + new_fernet.encrypt(plain).decode()
        await conn.execute(
            "UPDATE nf_api_keys SET encrypted_value = $1 WHERE id = $2",
            new_cipher, row["id"],
        )
    await conn.close()

asyncio.run(main())
```

Run this script with both `JWT_SECRET_OLD` and `JWT_SECRET_NEW` set
in the env. Confirm the script reports the row count and exits 0
before proceeding.

### Step 3 -- Rotate the env var on Render

> **CRITICAL**: per the project's operational rules, NEVER use a
> raw PUT to Render's `/env-vars` API without ALL existing vars in
> the payload. Use the dashboard or the documented bulk-update
> command. A naive PUT clobbers DATABASE_URL / STRIPE_* / etc.

- Update `JWT_SECRET` in Render dashboard to the new value.
- Wait for Render's redeploy (~2 minutes).
- Confirm the deploy succeeded via `nexusforge status` or hitting
  `/api/health` from the public URL.

### Step 4 -- Validate

- [ ] Hit `/api/health` from production. 200 OK.
- [ ] Existing logged-in users will get 401 on next request (their
      tokens were signed with the OLD secret) -- expected. Force
      re-login via the frontend.
- [ ] Pick one user with stored API keys. Have them test an
      integration that uses one of those keys (e.g. a workflow
      that calls Anthropic). The decrypted key should still work
      because we re-encrypted in Step 2.
- [ ] Check Mythos: run `render exec <service> -- python -c
      "from app.security.mythos import _derive_mythos_key;
      print(_derive_mythos_key())"` -- this prints the NEW Mythos
      key. The previous key is dead.

### Step 5 -- Post-rotation cleanup

- [ ] Burn the OLD `JWT_SECRET` from password manager (after
      verifying re-encryption took, since old cipher rows are
      irrecoverable without it).
- [ ] Update the Mythos client tooling / scripts that hit
      `/api/mythos/*` with the new derived key.
- [ ] Log the rotation: who/when/why in
      `docs/runbooks/key-rotation-log.md` (create if missing).

---

## What still needs to be built

The 3 weaknesses listed in the original runbook have ALL been
addressed in the H-2 work (2026-04-27):

- ~~No `MultiFernet` overlap~~ → shipped in Phase 2 (`89d2949`).
  See "Rotate the Fernet key" above for the new flow.
- ~~No JWT secret split~~ → shipped in Phase 1 (`c0431bb`). Three
  independent env vars + accessor module
  (`backend/app/auth/secrets.py`).
- ~~No fingerprint emission at boot~~ → shipped in A-03 (2026-04-25,
  commit `b24f6ee`) and expanded in Phase 1 to per-surface
  fingerprints. Look for `secret fingerprint <name>: <16-hex>`
  lines in stdout / log aggregator at app startup.

All three weaknesses listed in the original runbook have been
addressed:

- ~~Per-tenant Fernet rotation has no overlap window~~ → shipped
  2026-04-27 (`91c50bf`, `TENANT_FERNET_IKM_OLD` MultiFernet
  wrapper) + 2026-04-30 (per-tenant migration script). See
  "Per-tenant Fernet rotation" above.
- ~~No `revoke_all_refresh_tokens` admin endpoint~~ → shipped
  2026-04-27 (`91c50bf`,
  `POST /api/admin/users/{id}/refresh-tokens/revoke-all`).
- **No Mythos key fingerprint in scan reports** — still open.
  Cosmetic; would let ops verify a Mythos rotation took effect
  without re-running `_derive_mythos_key` on the container.

---

## Emergency rotation (suspected leak)

If `JWT_SECRET` is suspected leaked (e.g. accidentally committed,
visible in a screenshot, exfil indicators in logs):

1. Skip Step 1 prep -- start the procedure immediately.
2. After Step 3 deploy, force-revoke every active JWT by calling
   `/auth/logout` for every user via an admin script, OR (faster)
   restart the backend twice in quick succession to flush all
   existing sessions through the 401 path.
3. After Step 5, force-rotate the most-sensitive stored API keys
   (Stripe live, Anthropic prod) since the database row was
   encrypted with the leaked key for some window of time.
