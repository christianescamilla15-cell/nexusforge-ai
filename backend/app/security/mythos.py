"""Mythos — Advanced Internal Security Auditor for NexusForge AI.

OWNER-ONLY tool. Protected by MYTHOS_KEY derived from JWT_SECRET.
Scans the entire platform for vulnerabilities:
  - Hardcoded secrets and credential leaks
  - Auth enforcement gaps (unprotected endpoints)
  - Injection vectors (SQLi, XSS, command injection)
  - Cryptographic weaknesses (JWT, encryption, hashing)
  - CORS and header misconfiguration
  - Rate limiting coverage
  - Dependency vulnerabilities
  - Memory and data exposure risks

NEVER expose this module to end users or public APIs.
"""

import hashlib
import hmac
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Access Control ──────────────────────────────────────────────────────────

def _derive_mythos_key() -> str:
    """Derive Mythos access key from JWT_SECRET. Only the owner knows JWT_SECRET."""
    from app.config import settings
    return hmac.new(
        settings.jwt_secret.encode(),
        b"mythos-nexusforge-admin-2026",
        hashlib.sha512,
    ).hexdigest()[:64]


def verify_mythos_access(provided_key: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    expected = _derive_mythos_key()
    return hmac.compare_digest(provided_key, expected)


# ── Data Models ─────────────────────────────────────────────────────────────

@dataclass
class Finding:
    severity: str       # critical, high, medium, low, info
    category: str       # secrets, auth, injection, crypto, config, deps, data
    title: str
    description: str
    file_path: str = ""
    line_number: int = 0
    remediation: str = ""
    cwe: str = ""       # CWE reference

@dataclass
class AuditReport:
    timestamp: float = field(default_factory=time.time)
    duration_ms: int = 0
    findings: list[Finding] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    scanned_files: int = 0
    scanned_endpoints: int = 0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "total_findings": len(self.findings),
            "by_severity": self._count_by("severity"),
            "by_category": self._count_by("category"),
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "title": f.title,
                    "description": f.description,
                    "file": f.file_path,
                    "line": f.line_number,
                    "remediation": f.remediation,
                    "cwe": f.cwe,
                }
                for f in sorted(self.findings, key=lambda x: _SEV_ORDER.get(x.severity, 5))
            ],
            "scanned_files": self.scanned_files,
            "scanned_endpoints": self.scanned_endpoints,
            "score": self._security_score(),
        }

    def _count_by(self, attr: str) -> dict:
        counts: dict[str, int] = {}
        for f in self.findings:
            val = getattr(f, attr)
            counts[val] = counts.get(val, 0) + 1
        return counts

    def _security_score(self) -> int:
        """0-100 security score. Deductions per finding severity."""
        score = 100
        for f in self.findings:
            score -= _SEV_DEDUCTION.get(f.severity, 1)
        return max(0, score)


_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_SEV_DEDUCTION = {"critical": 15, "high": 8, "medium": 3, "low": 1, "info": 0}


# ── Scanner Engine ──────────────────────────────────────────────────────────

class MythosScanner:
    """Core security scanner. Run all checks and produce a unified report."""

    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.backend = self.root / "backend"
        self.frontend = self.root / "frontend"
        self.findings: list[Finding] = []
        # Phase 6 — diff-aware scan support. When set to a non-None
        # frozenset of resolved absolute Paths, file-based scanners
        # only process files in the allowlist. None = scan everything
        # (legacy full-scan behavior, unchanged).
        self._file_allowlist: frozenset[Path] | None = None

    def _should_scan(self, fpath: Path) -> bool:
        """Return True if ``fpath`` is in the current allowlist (or if
        no allowlist is set). Used by file-walking scanners to skip
        non-diff files when running in diff-aware mode."""
        if self._file_allowlist is None:
            return True
        try:
            return fpath.resolve() in self._file_allowlist
        except OSError:
            return False

    async def full_scan(self) -> AuditReport:
        """Execute all security checks."""
        start = time.monotonic()

        files_scanned = 0
        endpoints_scanned = 0

        # 1. Secret scanning
        files_scanned += self._scan_secrets()

        # 2. Auth enforcement
        endpoints_scanned += self._scan_auth_enforcement()

        # 3. Injection vectors
        files_scanned += self._scan_injection_vectors()

        # 4. Crypto weaknesses
        self._scan_crypto()

        # 5. Config & headers
        self._scan_config()

        # 6. Rate limiting coverage
        self._scan_rate_limits()

        # 7. Data exposure
        self._scan_data_exposure()

        # 8. Dependency audit
        self._scan_dependencies()

        # 9. Frontend security
        files_scanned += self._scan_frontend_security()

        duration = int((time.monotonic() - start) * 1000)

        report = AuditReport(
            duration_ms=duration,
            findings=self.findings,
            scanned_files=files_scanned,
            scanned_endpoints=endpoints_scanned,
        )
        return report

    # ── Phase 6 — Diff-aware scan ───────────────────────────────────────────
    #
    # Runs the file-walking scanners (secrets + injection) scoped to an
    # explicit list of changed files, instead of the whole project tree.
    # The caller is responsible for computing the diff (typically via
    # `git diff --name-only <base>...<head>`) and posting the resulting
    # list to POST /api/mythos/scan/diff.
    #
    # Non-file scanners (crypto, config, rate limits, dependencies) are
    # skipped in diff mode: they analyze a fixed set of well-known config
    # files (jwt_handler.py, requirements.txt, etc.) which rarely change
    # in a typical PR, and running them on every diff scan adds noise
    # without providing incremental value. The full scan endpoint is
    # still the right tool for tenant-wide audits.

    async def diff_scan(self, changed_files: list[str]) -> AuditReport:
        """Run file-walking security scanners against a bounded allowlist
        of changed files.

        Args:
            changed_files: list of paths RELATIVE to the project root
                (e.g. ``backend/app/routes/foo.py``). Absolute paths and
                paths that escape the project root are silently skipped.
                Missing files are also skipped — no error is raised for
                a deleted file in the diff.

        Returns:
            An AuditReport with findings scoped to the allowed files.
            ``scanned_files`` counts only files that actually passed
            path safety and existence checks (may be < ``len(changed_files)``).
        """
        start = time.monotonic()

        # Resolve the allowlist: turn each relative path into an absolute
        # Path, drop anything that fails safety or doesn't exist.
        root_resolved = self.root.resolve()
        allow: set[Path] = set()
        for rel in changed_files:
            if not rel or "\x00" in rel:
                continue
            # Refuse absolute paths and obvious traversal
            candidate = Path(rel)
            if candidate.is_absolute() or ".." in candidate.parts:
                logger.debug("Mythos diff-scan: refused unsafe path %r", rel)
                continue
            abs_path = (self.root / rel).resolve()
            try:
                abs_path.relative_to(root_resolved)
            except ValueError:
                logger.debug("Mythos diff-scan: path escapes root %r", rel)
                continue
            if not abs_path.is_file():
                continue
            allow.add(abs_path)

        self._file_allowlist = frozenset(allow)
        self.findings = []  # fresh report, don't inherit any prior state

        try:
            files_scanned = 0

            # Only the file-walking scanners are scoped. Non-file-walking
            # scanners (crypto, config, rate limits, dependencies, auth)
            # look at fixed known paths and are skipped in diff mode.
            files_scanned += self._scan_secrets()
            files_scanned += self._scan_injection_vectors()
            files_scanned += self._scan_frontend_security()
        finally:
            # Always clear the allowlist on exit so a subsequent full
            # scan on the same scanner instance does not silently
            # inherit the scoped state.
            self._file_allowlist = None

        duration = int((time.monotonic() - start) * 1000)

        report = AuditReport(
            duration_ms=duration,
            findings=self.findings,
            scanned_files=files_scanned,
            scanned_endpoints=0,  # auth scanner not run in diff mode
        )
        return report

    # ── 1. Secret Scanner ───────────────────────────────────────────────────

    _SECRET_PATTERNS = [
        (r'(?i)(api[_-]?key|secret|password|token|credential)\s*[=:]\s*["\']([^"\']{8,})["\']', "Hardcoded secret"),
        (r'(?i)(sk-ant-|sk-[a-zA-Z0-9]{20,})', "Anthropic API key"),
        (r'(?i)(gsk_[a-zA-Z0-9]{20,})', "Groq API key"),
        (r'(?i)(ghp_[a-zA-Z0-9]{36})', "GitHub personal token"),
        (r'(?i)(xox[baprs]-[a-zA-Z0-9-]{10,})', "Slack token"),
        (r'(?i)(AKIA[0-9A-Z]{16})', "AWS access key"),
        (r'(?i)(mongodb\+srv://[^"\'>\s]+)', "MongoDB connection string with credentials"),
        (r'(?i)(postgres(?:ql)?://[^@\s]+@[^"\'>\s]+)', "PostgreSQL connection string"),
        (r'(?i)(redis://:[^@\s]+@[^"\'>\s]+)', "Redis connection with password"),
        (r'(?i)Bearer\s+[a-zA-Z0-9._-]{20,}', "Hardcoded bearer token"),
    ]

    _SECRET_IGNORE_PATTERNS = [
        r'\.env',           # env files are expected to have secrets
        r'example',         # example files
        r'test_',           # test files may have test tokens
        r'conftest',
        r'__pycache__',
        r'node_modules',
        r'\.git/',
        r'dist/',
        r'security[\\/]mythos\.py',  # Don't scan ourselves (pattern definitions)
    ]

    def _scan_secrets(self) -> int:
        """Scan all source files for hardcoded secrets."""
        count = 0
        for ext in ("*.py", "*.js", "*.jsx", "*.json", "*.yml", "*.yaml", "*.toml"):
            for fpath in self.root.rglob(ext):
                rel = str(fpath.relative_to(self.root))
                if any(re.search(p, rel) for p in self._SECRET_IGNORE_PATTERNS):
                    continue
                if not self._should_scan(fpath):
                    continue
                count += 1
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    for line_num, line in enumerate(content.splitlines(), 1):
                        for pattern, desc in self._SECRET_PATTERNS:
                            if re.search(pattern, line):
                                # Skip if it's an env var reference
                                if "os.environ" in line or "getenv" in line or "settings." in line:
                                    continue
                                if "${" in line or "$(" in line:
                                    continue
                                self.findings.append(Finding(
                                    severity="critical",
                                    category="secrets",
                                    title=f"{desc} detected",
                                    description=f"Potential secret found: {line.strip()[:80]}...",
                                    file_path=rel,
                                    line_number=line_num,
                                    remediation="Move to environment variable or secrets manager",
                                    cwe="CWE-798",
                                ))
                except Exception:
                    pass
        return count

    # ── 2. Auth Enforcement Scanner ─────────────────────────────────────────

    def _scan_auth_enforcement(self) -> int:
        """Check all route files for auth enforcement gaps."""
        routes_dir = self.backend / "app" / "routes"
        if not routes_dir.exists():
            return 0

        endpoint_count = 0
        for fpath in routes_dir.glob("*.py"):
            rel = str(fpath.relative_to(self.root))
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()

                for i, line in enumerate(lines, 1):
                    # Find endpoint definitions
                    ep_match = re.search(r'@router\.(get|post|put|delete|patch|websocket)\(', line)
                    if not ep_match:
                        continue
                    endpoint_count += 1

                    # Check next 15 lines for auth check
                    block = "\n".join(lines[i:i+15])
                    has_auth = any(p in block for p in [
                        "_get_user_id", "get_user_id", "request.state.user",
                        "verify_token", "Depends(", "check_rate_limit",
                        "Authorization",
                    ])

                    if not has_auth:
                        self.findings.append(Finding(
                            severity="high",
                            category="auth",
                            title="Endpoint without auth check",
                            description=f"Endpoint at line {i} has no visible auth verification",
                            file_path=rel,
                            line_number=i,
                            remediation="Add _get_user_id(request) or auth dependency",
                            cwe="CWE-862",
                        ))
            except Exception:
                pass
        return endpoint_count

    # ── 3. Injection Scanner ────────────────────────────────────────────────

    _SQL_INJECTION_PATTERNS = [
        (r'f["\'].*SELECT.*\{', "Potential SQL injection via f-string"),
        (r'f["\'].*INSERT.*\{', "Potential SQL injection via f-string"),
        (r'f["\'].*UPDATE.*\{', "Potential SQL injection via f-string"),
        (r'f["\'].*DELETE.*\{', "Potential SQL injection via f-string"),
        (r'\.format\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE)', "Potential SQL injection via .format()"),
        (r'%s.*(?:SELECT|INSERT|UPDATE|DELETE).*%\s*\(', "Potential SQL injection via % formatting"),
    ]

    _COMMAND_INJECTION_PATTERNS = [
        (r'subprocess\.\w+\(.*(shell\s*=\s*True)', "Command injection: shell=True"),
        (r'os\.system\(', "Command injection: os.system()"),
        (r'os\.popen\(', "Command injection: os.popen()"),
        (r'eval\(', "Code injection: eval()"),
        (r'exec\((?!ute)', "Code injection: exec()"),
    ]

    _XSS_PATTERNS = [
        (r'dangerouslySetInnerHTML', "Potential XSS via dangerouslySetInnerHTML"),
        (r'\.innerHTML\s*=', "Potential XSS via innerHTML"),
        (r'document\.write\(', "Potential XSS via document.write"),
    ]

    def _scan_injection_vectors(self) -> int:
        """Scan for SQL injection, command injection, and XSS."""
        count = 0

        # Backend: SQL + Command injection
        for fpath in self.backend.rglob("*.py"):
            if "__pycache__" in str(fpath) or "security" in str(fpath):
                continue
            if not self._should_scan(fpath):
                continue
            rel = str(fpath.relative_to(self.root))
            count += 1
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern, desc in self._SQL_INJECTION_PATTERNS:
                        if re.search(pattern, line, re.IGNORECASE):
                            self.findings.append(Finding(
                                severity="critical",
                                category="injection",
                                title=desc,
                                description=f"Line: {line.strip()[:100]}",
                                file_path=rel,
                                line_number=line_num,
                                remediation="Use parameterized queries ($1, $2) instead of string interpolation",
                                cwe="CWE-89",
                            ))
                    for pattern, desc in self._COMMAND_INJECTION_PATTERNS:
                        if re.search(pattern, line):
                            self.findings.append(Finding(
                                severity="critical",
                                category="injection",
                                title=desc,
                                description=f"Line: {line.strip()[:100]}",
                                file_path=rel,
                                line_number=line_num,
                                remediation="Use subprocess.run() with shell=False and list args",
                                cwe="CWE-78",
                            ))
            except Exception:
                pass

        # Frontend: XSS
        for fpath in self.frontend.rglob("*.jsx"):
            if "node_modules" in str(fpath):
                continue
            if not self._should_scan(fpath):
                continue
            rel = str(fpath.relative_to(self.root))
            count += 1
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern, desc in self._XSS_PATTERNS:
                        if re.search(pattern, line):
                            self.findings.append(Finding(
                                severity="high",
                                category="injection",
                                title=desc,
                                description=f"Line: {line.strip()[:100]}",
                                file_path=rel,
                                line_number=line_num,
                                remediation="Sanitize input or use React's default text escaping",
                                cwe="CWE-79",
                            ))
            except Exception:
                pass

        return count

    # ── 4. Crypto Auditor ───────────────────────────────────────────────────

    def _scan_crypto(self):
        """Audit cryptographic implementations."""
        # Check JWT configuration
        jwt_file = self.backend / "app" / "auth" / "jwt_handler.py"
        if jwt_file.exists():
            content = jwt_file.read_text(encoding="utf-8", errors="ignore")

            if "HS256" in content and "RS256" not in content:
                self.findings.append(Finding(
                    severity="medium",
                    category="crypto",
                    title="JWT uses HS256 (symmetric signing)",
                    description="HS256 requires sharing the secret key. RS256 (asymmetric) is more secure for distributed systems.",
                    file_path=str(jwt_file.relative_to(self.root)),
                    remediation="Consider RS256 for production if multiple services verify tokens",
                    cwe="CWE-327",
                ))

            if "refresh" not in content.lower():
                self.findings.append(Finding(
                    severity="medium",
                    category="crypto",
                    title="No refresh token implementation",
                    description="Long-lived access tokens increase window of exposure if compromised.",
                    file_path=str(jwt_file.relative_to(self.root)),
                    remediation="Implement refresh tokens with short-lived access tokens (15-30 min)",
                    cwe="CWE-613",
                ))

        # Check encryption module
        enc_file = self.backend / "app" / "auth" / "encryption.py"
        if enc_file.exists():
            content = enc_file.read_text(encoding="utf-8", errors="ignore")
            has_fernet = "fernet" in content.lower() or "Fernet" in content
            has_xor_only = ("^ key_stream" in content) and not has_fernet
            if has_xor_only:
                self.findings.append(Finding(
                    severity="high",
                    category="crypto",
                    title="API key encryption uses XOR only (weak)",
                    description="XOR-based encryption without IV is deterministic — identical plaintext produces identical ciphertext.",
                    file_path=str(enc_file.relative_to(self.root)),
                    remediation="Upgrade to Fernet (cryptography package) or AES-256-GCM with random IV",
                    cwe="CWE-327",
                ))
            elif has_fernet and "^ key_stream" in content:
                self.findings.append(Finding(
                    severity="info",
                    category="crypto",
                    title="API key encryption upgraded to Fernet (legacy XOR kept for backward compat)",
                    description="Fernet (AES-128-CBC + HMAC) is the primary encryption. Legacy XOR is kept for decrypting old values.",
                    file_path=str(enc_file.relative_to(self.root)),
                    remediation="Re-encrypt all existing keys with Fernet to remove legacy XOR dependency",
                    cwe="CWE-327",
                ))

    # ── 5. Config & Headers ─────────────────────────────────────────────────

    def _scan_config(self):
        """Check security configuration."""
        main_file = self.backend / "app" / "main.py"
        if not main_file.exists():
            return

        content = main_file.read_text(encoding="utf-8", errors="ignore")

        # Check CORS
        if 'allow_origins=["*"]' in content or "allow_origins=['*']" in content:
            self.findings.append(Finding(
                severity="high",
                category="config",
                title="CORS allows all origins (wildcard)",
                description="CORS wildcard allows any website to make authenticated requests to the API.",
                file_path=str(main_file.relative_to(self.root)),
                remediation="Set specific allowed origins in ALLOWED_ORIGINS env var",
                cwe="CWE-942",
            ))

        # Check if debug mode indicators
        if "debug=True" in content or "DEBUG=True" in content:
            self.findings.append(Finding(
                severity="high",
                category="config",
                title="Debug mode enabled in main.py",
                description="Debug mode may expose stack traces and internal state to attackers.",
                file_path=str(main_file.relative_to(self.root)),
                remediation="Set DEBUG=false in production",
                cwe="CWE-489",
            ))

        # Check security headers
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "HSTS",
        }
        for header, desc in required_headers.items():
            if header not in content:
                self.findings.append(Finding(
                    severity="medium",
                    category="config",
                    title=f"Missing security header: {header}",
                    description=f"{desc} header not found in middleware configuration.",
                    file_path=str(main_file.relative_to(self.root)),
                    remediation=f"Add {header} to SecurityHeadersMiddleware",
                    cwe="CWE-693",
                ))

        # Check middleware order (CORS must be last added = outermost)
        # In Starlette, last add_middleware() = outermost wrapper
        cors_pos = content.find("app.add_middleware(\n    CORSMiddleware") if "CORSMiddleware" in content else -1
        auth_pos = content.find("app.add_middleware(AuthMiddleware)")
        if cors_pos > 0 and auth_pos > 0 and cors_pos < auth_pos:
            self.findings.append(Finding(
                severity="high",
                category="config",
                title="CORS middleware not outermost",
                description="CORS must be added AFTER auth (last add_middleware = outermost). Currently auth is added after CORS.",
                file_path=str(main_file.relative_to(self.root)),
                remediation="Move app.add_middleware(CORSMiddleware, ...) to be the LAST middleware added",
                cwe="CWE-942",
            ))

    # ── 6. Rate Limiting ────────────────────────────────────────────────────

    def _scan_rate_limits(self):
        """Check rate limiting coverage."""
        routes_dir = self.backend / "app" / "routes"
        if not routes_dir.exists():
            return

        execution_endpoints = []
        for fpath in routes_dir.glob("*.py"):
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            rel = str(fpath.relative_to(self.root))

            # Find POST endpoints that trigger execution (expensive operations)
            if re.search(r'@router\.post.*\n.*(?:execute|run|trigger|process|generate)', content, re.MULTILINE):
                if "check_rate_limit" not in content:
                    self.findings.append(Finding(
                        severity="medium",
                        category="auth",
                        title=f"Execution endpoint without rate limit: {fpath.name}",
                        description="POST endpoints that trigger expensive operations should have rate limiting.",
                        file_path=rel,
                        remediation="Add: from app.auth.rate_limit import check_rate_limit; await check_rate_limit(request)",
                        cwe="CWE-770",
                    ))

    # ── 7. Data Exposure ────────────────────────────────────────────────────

    def _scan_data_exposure(self):
        """Check for sensitive data in logs, responses, and error messages."""
        for fpath in self.backend.rglob("*.py"):
            if "__pycache__" in str(fpath):
                continue
            rel = str(fpath.relative_to(self.root))
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for line_num, line in enumerate(content.splitlines(), 1):
                    # Logging sensitive data
                    if re.search(r'log.*\.(info|debug|warning|error).*(?:password|secret|token|api_key)', line, re.IGNORECASE):
                        if "mask" not in line.lower() and "redact" not in line.lower():
                            self.findings.append(Finding(
                                severity="high",
                                category="data",
                                title="Potential sensitive data in logs",
                                description=f"Line: {line.strip()[:100]}",
                                file_path=rel,
                                line_number=line_num,
                                remediation="Mask or redact sensitive values before logging",
                                cwe="CWE-532",
                            ))

                    # Stack trace exposure
                    if re.search(r'detail\s*=\s*str\(exc\)|detail\s*=\s*str\(e\)', line):
                        self.findings.append(Finding(
                            severity="medium",
                            category="data",
                            title="Exception details exposed to client",
                            description="Internal error details in HTTP responses can reveal implementation details.",
                            file_path=rel,
                            line_number=line_num,
                            remediation="Return generic error message; log full exception server-side",
                            cwe="CWE-209",
                        ))
            except Exception:
                pass

    # ── 8. Dependencies ─────────────────────────────────────────────────────

    def _scan_dependencies(self):
        """Check for known vulnerable or outdated dependencies."""
        req_file = self.backend / "requirements.txt"
        if not req_file.exists():
            return

        content = req_file.read_text(encoding="utf-8", errors="ignore")
        deps = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*[=<>!~]+\s*([0-9.]+)', line)
            if match:
                deps[match.group(1).lower()] = match.group(2)

        # Check for known issues
        if "pyjwt" in deps:
            version = deps["pyjwt"]
            if version < "2.4":
                self.findings.append(Finding(
                    severity="high",
                    category="deps",
                    title=f"PyJWT {version} may have vulnerabilities",
                    description="PyJWT versions < 2.4 have known algorithm confusion vulnerabilities.",
                    file_path="backend/requirements.txt",
                    remediation="Upgrade to PyJWT >= 2.8",
                    cwe="CWE-1104",
                ))

        if "cryptography" not in deps:
            self.findings.append(Finding(
                severity="medium",
                category="deps",
                title="cryptography package not installed",
                description="Without the cryptography package, API key encryption uses weak XOR obfuscation.",
                file_path="backend/requirements.txt",
                remediation="pip install cryptography; upgrade encryption.py to use Fernet",
                cwe="CWE-327",
            ))

    # ── 9. Frontend Security ────────────────────────────────────────────────

    def _scan_frontend_security(self) -> int:
        """Check frontend for security issues."""
        count = 0
        src_dir = self.frontend / "src"
        if not src_dir.exists():
            return 0

        for fpath in src_dir.rglob("*.jsx"):
            if "node_modules" in str(fpath):
                continue
            if not self._should_scan(fpath):
                continue
            rel = str(fpath.relative_to(self.root))
            count += 1
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for line_num, line in enumerate(content.splitlines(), 1):
                    # localStorage token storage (acceptable but noteworthy)
                    if "localStorage.setItem" in line and ("token" in line.lower() or "nf_token" in line):
                        self.findings.append(Finding(
                            severity="low",
                            category="data",
                            title="Auth token stored in localStorage",
                            description="localStorage is accessible to any JS on the page. HttpOnly cookies are more secure.",
                            file_path=rel,
                            line_number=line_num,
                            remediation="Consider HttpOnly cookies for token storage (prevents XSS token theft)",
                            cwe="CWE-922",
                        ))

                    # Open redirect
                    if re.search(r'window\.location\s*=\s*(?:.*\.url|.*data)', line):
                        self.findings.append(Finding(
                            severity="medium",
                            category="injection",
                            title="Potential open redirect",
                            description=f"Dynamic redirect: {line.strip()[:80]}",
                            file_path=rel,
                            line_number=line_num,
                            remediation="Validate redirect URL against allowlist",
                            cwe="CWE-601",
                        ))
            except Exception:
                pass
        return count
