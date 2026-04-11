"""Mythos Admin Routes — OWNER-ONLY security auditing endpoints.

All endpoints require X-Mythos-Key header with the correct derived key.
The key is derived from JWT_SECRET, so only the platform owner can access it.

To get your key: python -c "from app.security.mythos import _derive_mythos_key; print(_derive_mythos_key())"
"""

import logging
import os
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from app.security.mythos import MythosScanner, verify_mythos_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mythos", tags=["mythos-admin"])


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

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    scanner = MythosScanner(project_root)
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

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    scanner = MythosScanner(project_root)

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

    report = scanner.full_scan  # Use existing findings
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

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    scanner = MythosScanner(project_root)
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


@router.get("/key")
async def get_mythos_key(request: Request):
    """Get Mythos admin key (only works from localhost).

    This endpoint ONLY responds to requests from 127.0.0.1/localhost.
    """
    client_ip = request.client.host if request.client else ""
    if client_ip not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=404, detail="Not found")

    from app.security.mythos import _derive_mythos_key
    return {"mythos_key": _derive_mythos_key(), "warning": "KEEP THIS KEY SECRET. Do not share or commit."}
