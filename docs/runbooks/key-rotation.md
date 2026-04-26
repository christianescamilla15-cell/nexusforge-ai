# Runbook -- JWT_SECRET key rotation

**Owner**: Christian Hernandez
**Last updated**: 2026-04-25 (created in response to A-01 / M-9 from
[2026-04-25 internal retro](../audits/2026-04-25-internal-retro.md))

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

The current procedure has 3 known weaknesses, all tracked under
**H-2 (full)** in the 2026-04-25 retro:

1. **No `MultiFernet` overlap**: the re-encryption script is a
   stop-the-world operation. A `MultiFernet(new, old)` window
   would let us roll forward gradually.
2. **No JWT secret split**: `JWT_SIGNING_SECRET` / `MYTHOS_HMAC_SECRET`
   / `FERNET_KEY` should be three independent env vars so JWT
   rotation doesn't cascade.
3. **No fingerprint emission at boot**: there's no way to tell from
   request logs which `JWT_SECRET` version a process was started
   with. Logging `sha256(secret)[:16]` at app boot is a 5-line fix
   (A-03 in the retro) and would make rotation auditable in
   production.

Until those land, treat key rotation as a planned-maintenance
event with mandatory user-facing communication and the manual
Step 2 migration above.

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
