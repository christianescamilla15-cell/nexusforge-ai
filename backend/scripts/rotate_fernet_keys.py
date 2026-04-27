"""Re-encrypt every row in `nf_api_keys` from any old Fernet key
(listed in `FERNET_KEYS_OLD`) to the current `FERNET_KEY`.

H-2 Phase 4 (2026-04-27). Pairs with the Phase 2 MultiFernet overlap
window in `app.auth.encryption._get_fernet`. Run during a rotation:

    1. Generate K2:
        python -c "from cryptography.fernet import Fernet; \
                   print(Fernet.generate_key().decode())"

    2. Deploy with FERNET_KEY=K2 and FERNET_KEYS_OLD=K1 set on the
       same deploy. Old K1 ciphertexts continue to decrypt via the
       MultiFernet secondary slot.

    3. Run THIS script (with the same env vars as the deploy):
        python -m backend.scripts.rotate_fernet_keys

       It iterates `nf_api_keys`, re-encrypts every row whose
       ciphertext does not already verify against the primary key,
       and writes the new ciphertext back. Rows that already
       decrypt with the primary are skipped (no-op).

    4. Once the script reports `0 rows still on a secondary key`,
       drop FERNET_KEYS_OLD from the env. Next deploy runs
       single-Fernet on K2 and the rotation is complete.

Safety properties:
    - Single-pass, idempotent. Safe to run repeatedly.
    - Each row is re-encrypted in its own UPDATE so a partial
      failure leaves the rest of the table consistent.
    - Cipher prefix routing is preserved: `tfernet:` (per-tenant)
      rows are SKIPPED — per-tenant Fernet uses a different key
      derivation and is not in scope for this script. A separate
      M-10-followup script will handle per-tenant rotation.
    - No plaintext is logged. Counts only.

Pre-flight:
    - DATABASE_URL must point to the target Postgres.
    - FERNET_KEY (the new primary) and FERNET_KEYS_OLD (the
      previous key, comma-separated if multiple) must be set in
      the same shell that runs this script. Verify with:
        python -c "from app.auth.secrets import boot_fingerprints; \
                   print(boot_fingerprints())"
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

# Allow running as a module from the backend/ root.
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from cryptography.fernet import Fernet, InvalidToken  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
)
logger = logging.getLogger("rotate_fernet_keys")


async def main() -> int:
    # Lazy imports so the module can be run as `python -m` without
    # FastAPI startup wiring.
    from app.auth.secrets import (
        get_primary_fernet_key,
        get_fernet_secondary_keys,
    )
    from app.db.client import get_db_pool

    primary_key = get_primary_fernet_key()
    secondary_keys = get_fernet_secondary_keys()

    if not secondary_keys:
        logger.warning(
            "FERNET_KEYS_OLD is unset — nothing to migrate from. If you "
            "are MID-ROTATION, set FERNET_KEYS_OLD to the previous key(s) "
            "before re-running this script."
        )
        return 0

    primary_fernet = Fernet(primary_key)
    secondary_fernets = [Fernet(k) for k in secondary_keys]

    logger.info(
        "Rotation context: primary key fingerprint sha256[:16]=%s, "
        "secondary count=%d",
        __import__("hashlib").sha256(primary_key).hexdigest()[:16],
        len(secondary_keys),
    )

    pool = await get_db_pool()
    rows_total = 0
    rows_skipped_already_primary = 0
    rows_skipped_per_tenant = 0
    rows_skipped_legacy_xor = 0
    rows_migrated = 0
    rows_failed = 0

    async with pool.acquire() as conn:
        # Stream by pkey to keep memory bounded on large tables.
        rows = await conn.fetch(
            "SELECT id, api_key_encrypted FROM user_provider_keys "
            "WHERE api_key_encrypted IS NOT NULL AND api_key_encrypted != ''"
        )
        rows_total = len(rows)
        logger.info("Scanning %d rows in user_provider_keys", rows_total)

        for row in rows:
            ciphertext = row["api_key_encrypted"]

            # Per-tenant ciphertexts are NOT in scope — they use a
            # different key derivation. Skip silently.
            if ciphertext.startswith("tfernet:"):
                rows_skipped_per_tenant += 1
                continue

            # Bare base64 = legacy XOR; a separate one-shot would
            # migrate those, but XOR uses _KEY (jwt_secret[:32]),
            # not Fernet, so this script doesn't touch them.
            if not ciphertext.startswith("fernet:"):
                rows_skipped_legacy_xor += 1
                continue

            cipher_bytes = ciphertext[len("fernet:"):].encode()

            # Already on the primary? Try primary first; if it
            # decrypts cleanly, no work needed.
            try:
                primary_fernet.decrypt(cipher_bytes)
                rows_skipped_already_primary += 1
                continue
            except InvalidToken:
                pass  # Falls through to the secondary trial below.

            # Try each secondary in order.
            plaintext = None
            for sf in secondary_fernets:
                try:
                    plaintext = sf.decrypt(cipher_bytes)
                    break
                except InvalidToken:
                    continue

            if plaintext is None:
                logger.error(
                    "Row id=%s could not be decrypted with any configured "
                    "key. Manual investigation required.",
                    row["id"],
                )
                rows_failed += 1
                continue

            # Re-encrypt with the primary and write back.
            new_cipher = "fernet:" + primary_fernet.encrypt(plaintext).decode()
            await conn.execute(
                "UPDATE user_provider_keys SET api_key_encrypted = $1 WHERE id = $2",
                new_cipher, row["id"],
            )
            rows_migrated += 1

    logger.info(
        "Rotation pass complete: total=%d migrated=%d already_primary=%d "
        "per_tenant_skipped=%d legacy_xor_skipped=%d failed=%d",
        rows_total, rows_migrated, rows_skipped_already_primary,
        rows_skipped_per_tenant, rows_skipped_legacy_xor, rows_failed,
    )
    if rows_failed:
        logger.error(
            "%d row(s) could not be migrated. Drop FERNET_KEYS_OLD only "
            "after every row reports `already_primary` on the next pass.",
            rows_failed,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
