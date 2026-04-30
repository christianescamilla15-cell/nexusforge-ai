"""Re-encrypt every per-tenant `tfernet:` row in `user_provider_keys`
from any old master IKM (listed in `TENANT_FERNET_IKM_OLD`) to the
current `JWT_SECRET` IKM.

M-10 followup (2026-04-30). Pairs with the MultiFernet overlap
added on 2026-04-27 in `app.auth.encryption._derive_tenant_fernet`.
Per-tenant Fernet keys are derived via:

    Fernet(b64(HKDF(ikm=jwt_secret, salt=tenant_id, info=...)))

The primary IKM is the current `JWT_SECRET`; secondaries come from
`TENANT_FERNET_IKM_OLD` (comma-separated). Standard MultiFernet
semantics — write uses primary, decrypt tries primary then each
secondary in order. This script forces every row off the
secondaries and onto the primary so the env var can be dropped.

Run during a per-tenant IKM rotation:

    1. Decouple sibling surfaces FIRST so rotating JWT_SECRET
       doesn't drag them along. Set in Render dashboard:
         - JWT_SIGNING_SECRET   (a different value from current JWT_SECRET)
         - MYTHOS_HMAC_SECRET   (a different value)
         - FERNET_KEY           (canonical 44-char Fernet key)
       After the next deploy, JWT_SECRET stops being a master key
       and becomes JUST the per-tenant IKM seed.

    2. Generate K2:
        python -c "import secrets; print(secrets.token_urlsafe(48))"

    3. Single deploy: set JWT_SECRET=K2 and TENANT_FERNET_IKM_OLD=K1
       (the previous JWT_SECRET). Old `tfernet:` rows continue
       to decrypt via the secondary slot.

    4. Run THIS script (with the same env vars as the deploy):
        python -m backend.scripts.rotate_tenant_fernet_keys

       It iterates every `tfernet:` row, attempts to decrypt with
       the row's tenant_id under the primary IKM first, falls
       through to each secondary IKM, and re-encrypts under the
       primary. Rows already on the primary are skipped (no-op).

    5. Once the script reports `failed=0` AND a re-run reports
       `migrated=0` (everything is `already_primary`), drop
       TENANT_FERNET_IKM_OLD from the env. Next deploy runs
       single-IKM and the rotation is complete.

Safety properties:
    - Idempotent. Safe to re-run; rows on the primary slot are
      detected because primary.decrypt() succeeds before the
      MultiFernet falls through to the secondaries.
    - Only `tfernet:` rows are touched. Global `fernet:` rows are
      handled by `rotate_fernet_keys.py`; legacy bare-base64 XOR
      rows are skipped (encrypt path is refused; decrypt-only stays).
    - Each row is re-encrypted in its own UPDATE so a partial
      failure leaves the rest of the table consistent.
    - No plaintext is logged. Counts and row ids only.

Pre-flight:
    - DATABASE_URL must point to the target Postgres.
    - JWT_SECRET (the new primary IKM) and TENANT_FERNET_IKM_OLD
      (the previous IKM(s), comma-separated if multiple) must be
      set in the same shell that runs this script. Verify with:
        python -c "from app.auth.secrets import boot_fingerprints; \
                   print(boot_fingerprints())"
      The `tenant_ikm_secondary_count` field should be > 0.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import sys
from pathlib import Path

# Allow running as a module from the backend/ root.
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from cryptography.fernet import InvalidToken  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
)
logger = logging.getLogger("rotate_tenant_fernet_keys")

_TFERNET_PREFIX = "tfernet:"


async def run_rotation_pass(pool) -> dict:
    """Run one re-encryption pass over `tfernet:` rows in
    `user_provider_keys.api_key_encrypted`.

    Pure logic — accepts an asyncpg-style pool, returns a counts dict.
    Kept separate from `main()` so admin HTTP handlers can call it
    without invoking sys.exit / CLI logging.

    Return shape:
        {
            "status": "no_op" | "complete" | "partial",
            "total": int, "migrated": int, "already_primary": int,
            "global_fernet_skipped": int, "legacy_xor_skipped": int,
            "no_user_id_skipped": int, "failed": int,
            "primary_ikm_fingerprint": str,     # sha256[:16] of current JWT_SECRET
            "secondary_ikm_count": int,         # 0 ⇒ status="no_op"
        }
    """
    from app.auth.encryption import _derive_tenant_fernet_for_ikm
    from app.auth.secrets import get_tenant_ikm_secondaries
    from app.config import settings

    primary_ikm = settings.jwt_secret.encode()
    secondary_ikms = get_tenant_ikm_secondaries()
    primary_fp = hashlib.sha256(primary_ikm).hexdigest()[:16]

    if not secondary_ikms:
        logger.warning(
            "TENANT_FERNET_IKM_OLD is unset — nothing to migrate from. "
            "If you are MID-ROTATION, set TENANT_FERNET_IKM_OLD to the "
            "previous JWT_SECRET(s) before re-running."
        )
        return {
            "status": "no_op",
            "reason": "TENANT_FERNET_IKM_OLD unset",
            "total": 0,
            "migrated": 0,
            "already_primary": 0,
            "global_fernet_skipped": 0,
            "legacy_xor_skipped": 0,
            "no_user_id_skipped": 0,
            "failed": 0,
            "primary_ikm_fingerprint": primary_fp,
            "secondary_ikm_count": 0,
        }

    logger.info(
        "Per-tenant rotation context: primary IKM fingerprint sha256[:16]=%s, "
        "secondary IKM count=%d",
        primary_fp, len(secondary_ikms),
    )

    rows_total = 0
    rows_skipped_already_primary = 0
    rows_skipped_global_fernet = 0
    rows_skipped_legacy_xor = 0
    rows_skipped_no_user_id = 0
    rows_migrated = 0
    rows_failed = 0

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, user_id, api_key_encrypted FROM user_provider_keys "
            "WHERE api_key_encrypted IS NOT NULL AND api_key_encrypted != ''"
        )
        rows_total = len(rows)
        logger.info("Scanning %d rows in user_provider_keys", rows_total)

        for row in rows:
            ciphertext = row["api_key_encrypted"]

            if ciphertext.startswith("fernet:"):
                rows_skipped_global_fernet += 1
                continue
            if not ciphertext.startswith(_TFERNET_PREFIX):
                rows_skipped_legacy_xor += 1
                continue

            user_id = row["user_id"]
            if not user_id:
                logger.error(
                    "Row id=%s has tfernet: ciphertext but NULL user_id "
                    "— manual investigation required.",
                    row["id"],
                )
                rows_skipped_no_user_id += 1
                continue
            tenant_id = str(user_id)
            cipher_bytes = ciphertext[len(_TFERNET_PREFIX):].encode()

            primary_fernet = _derive_tenant_fernet_for_ikm(tenant_id, primary_ikm)

            try:
                primary_fernet.decrypt(cipher_bytes)
                rows_skipped_already_primary += 1
                continue
            except InvalidToken:
                pass

            plaintext = None
            for old_ikm in secondary_ikms:
                old_fernet = _derive_tenant_fernet_for_ikm(tenant_id, old_ikm)
                try:
                    plaintext = old_fernet.decrypt(cipher_bytes)
                    break
                except InvalidToken:
                    continue

            if plaintext is None:
                logger.error(
                    "Row id=%s (tenant=%s) could not be decrypted with "
                    "any configured IKM. Manual investigation required.",
                    row["id"], tenant_id,
                )
                rows_failed += 1
                continue

            new_cipher = _TFERNET_PREFIX + primary_fernet.encrypt(plaintext).decode()
            await conn.execute(
                "UPDATE user_provider_keys SET api_key_encrypted = $1 WHERE id = $2",
                new_cipher, row["id"],
            )
            rows_migrated += 1

    logger.info(
        "Per-tenant rotation pass complete: total=%d migrated=%d "
        "already_primary=%d global_fernet_skipped=%d legacy_xor_skipped=%d "
        "no_user_id_skipped=%d failed=%d",
        rows_total, rows_migrated, rows_skipped_already_primary,
        rows_skipped_global_fernet, rows_skipped_legacy_xor,
        rows_skipped_no_user_id, rows_failed,
    )
    bad = rows_failed + rows_skipped_no_user_id
    if bad:
        logger.error(
            "%d row(s) could not be migrated. Drop TENANT_FERNET_IKM_OLD "
            "only after every row reports `already_primary` on a re-run.",
            bad,
        )

    return {
        "status": "partial" if bad else "complete",
        "total": rows_total,
        "migrated": rows_migrated,
        "already_primary": rows_skipped_already_primary,
        "global_fernet_skipped": rows_skipped_global_fernet,
        "legacy_xor_skipped": rows_skipped_legacy_xor,
        "no_user_id_skipped": rows_skipped_no_user_id,
        "failed": rows_failed,
        "primary_ikm_fingerprint": primary_fp,
        "secondary_ikm_count": len(secondary_ikms),
    }


async def main() -> int:
    from app.db.client import get_db_pool
    pool = await get_db_pool()
    result = await run_rotation_pass(pool)
    bad = result.get("failed", 0) + result.get("no_user_id_skipped", 0)
    return 1 if bad > 0 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
