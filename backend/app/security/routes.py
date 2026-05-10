"""Mythos Admin Routes — OWNER-ONLY security auditing endpoints.

All endpoints require X-Mythos-Key header with the correct derived key.
The key is derived from JWT_SECRET, so only the platform owner can access it.

To get your key: python -c "from app.security.mythos import _derive_mythos_key; print(_derive_mythos_key())"
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from app.security.mythos import MythosScanner, resolve_project_root, verify_mythos_access

logger = logging.getLogger(__name__)

# M-7 (2026-04-25): hide Mythos endpoints from /openapi.json so an
# attacker landing on a misconfigured staging deploy with DEBUG=true
# cannot enumerate the internal scanner surface from the OpenAPI doc.
router = APIRouter(
    prefix="/mythos",
    tags=["mythos-admin"],
    include_in_schema=False,
)


def _verify_admin(request: Request):
    """Verify the request has valid Mythos admin key."""
    key = request.headers.get("X-Mythos-Key", "")
    if not key or not verify_mythos_access(key):
        logger.warning(
            "Mythos: unauthorized access attempt from %s",
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/scan")
async def full_security_scan(request: Request):
    """Run a complete security audit of the NexusForge platform.

    Requires: X-Mythos-Key header
    Returns: Full audit report with findings, severity, and remediation.
    """
    _verify_admin(request)

    scanner = MythosScanner(str(resolve_project_root()))
    report = await scanner.full_scan()

    logger.info(
        "Mythos scan complete: %d findings (critical=%d, high=%d) in %dms",
        len(report.findings),
        report.to_dict()["by_severity"].get("critical", 0),
        report.to_dict()["by_severity"].get("high", 0),
        report.duration_ms,
    )

    return report.to_dict()


@router.post("/scan/{category}")
async def category_scan(category: str, request: Request):
    """Run a targeted scan for a specific category.

    Categories: secrets, auth, injection, crypto, config, deps, data
    Requires: X-Mythos-Key header
    """
    _verify_admin(request)

    valid_categories = {"secrets", "auth", "injection", "crypto", "config", "deps", "data"}
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Valid: {valid_categories}")

    scanner = MythosScanner(str(resolve_project_root()))

    # Run only the requested scanner
    scan_methods = {
        "secrets": lambda: scanner._scan_secrets(),
        "auth": lambda: scanner._scan_auth_enforcement(),
        "injection": lambda: scanner._scan_injection_vectors(),
        "crypto": lambda: scanner._scan_crypto(),
        "config": lambda: scanner._scan_config(),
        "deps": lambda: scanner._scan_dependencies(),
        "data": lambda: scanner._scan_data_exposure(),
    }

    scan_methods[category]()

    # Filter findings to requested category
    filtered = [f for f in scanner.findings if f.category == category]
    scanner.findings = filtered

    # M-5 (2026-04-25): removed `report = scanner.full_scan` — that
    # was a bound-method reference (missing `()`), not a call. The
    # category-scan response builds its dict directly from `filtered`
    # below, so the line was dead code masking what looked like an
    # attempt to invoke a 9-scanner full pass.
    return {
        "category": category,
        "findings_count": len(filtered),
        "findings": [
            {
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "file": f.file_path,
                "line": f.line_number,
                "remediation": f.remediation,
                "cwe": f.cwe,
            }
            for f in sorted(filtered, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(x.severity, 5))
        ],
    }


class MythosDiffScanRequest(BaseModel):
    """Request body for POST /api/mythos/scan/diff.

    Phase 6 — diff-aware Mythos scanning. The client is responsible
    for computing the changed-file list (e.g. via
    ``git diff --name-only <base>...<head>``) and posting it here.
    Running git inside the request path is intentionally avoided to
    eliminate shell-injection and missing-git risk on the server.
    """

    changed_files: list[str] = Field(
        ...,
        description=(
            "List of paths RELATIVE to the project root "
            "(e.g. 'backend/app/routes/foo.py'). Absolute paths "
            "or paths containing '..' are silently skipped. Max 500 "
            "entries per request."
        ),
        max_length=500,
    )


@router.post("/scan/diff")
async def diff_security_scan(body: MythosDiffScanRequest, request: Request):
    """Run a diff-aware security scan scoped to a changed-file list.

    Only runs the file-walking scanners (secrets, injection vectors,
    frontend security). Non-file scanners (crypto, config, deps,
    rate limits) are skipped — they look at a fixed set of known
    config files and rarely shift on a typical PR.

    Requires: X-Mythos-Key header (same as /scan and /scan/{category})
    """
    _verify_admin(request)

    scanner = MythosScanner(str(resolve_project_root()))
    report = await scanner.diff_scan(body.changed_files)

    logger.info(
        "Mythos diff-scan complete: %d findings across %d files in %dms",
        len(report.findings),
        report.scanned_files,
        report.duration_ms,
    )

    return {
        "mode": "diff",
        "requested_files": len(body.changed_files),
        "scanned_files": report.scanned_files,
        **report.to_dict(),
    }


# H-3 (2026-04-25): the `GET /mythos/key` endpoint was removed.
#
# The previous implementation gated access on `request.client.host in
# ("127.0.0.1", "::1", "localhost")`, but Render runs FastAPI behind a
# proxy. With Uvicorn started with `--proxy-headers` (or equivalently
# `forwarded_allow_ips="*"`, the default in the official Uvicorn Docker
# image), the framework trusts the X-Forwarded-For header by default —
# so an attacker over the public internet could send
# `curl -H "X-Forwarded-For: 127.0.0.1" https://.../api/mythos/key`
# and read the derived Mythos admin key.
#
# Operators retrieve the key out-of-band:
#   render exec <service> -- python -c "from app.security.mythos import _derive_mythos_key; print(_derive_mythos_key())"
# or, locally:
#   python -c "from app.security.mythos import _derive_mythos_key; print(_derive_mythos_key())"
#
# Documented in the file header docstring and in
# docs/audits/2026-04-25-internal-retro.md (H-3).
