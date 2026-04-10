"""Issue Triage Engine — prioritize 166K+ issues for enterprise-scale remediation.

Designed for enterprise-scale legacy systems:
  - 166,714 total issues across 31 apps + 57 components
  - 13,547 critical/blocker (8.1%)
  - 3,000+ SQL injection vulnerabilities
  - 25 PII data types across 318 inputs

Triage strategy:
  1. SEVERITY: critical/blocker first (CWE-weighted)
  2. EXPLOITABILITY: SQL injection > XSS > info leak (CVSS-like scoring)
  3. DATA EXPOSURE: PII-touching code gets priority boost
  4. BLAST RADIUS: shared modules (BusinessLayer.Shared) get priority boost
  5. FIX COMPLEXITY: easy wins first within same severity tier
  6. DEPENDENCY ORDER: fix leaves before shared components

Output: Ordered remediation plan with estimated effort per batch.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── CWE Severity Weights ───────────────────────────────────────────────────

_CWE_WEIGHTS = {
    # Critical (15-20 points)
    "CWE-89": 20,    # SQL Injection
    "CWE-78": 19,    # OS Command Injection
    "CWE-94": 18,    # Code Injection
    "CWE-502": 17,   # Deserialization
    "CWE-798": 16,   # Hardcoded Credentials
    "CWE-287": 15,   # Improper Authentication

    # High (10-14 points)
    "CWE-79": 14,    # XSS
    "CWE-862": 13,   # Missing Authorization
    "CWE-918": 12,   # SSRF
    "CWE-601": 11,   # Open Redirect
    "CWE-327": 10,   # Weak Crypto

    # Medium (5-9 points)
    "CWE-209": 9,    # Error Info Leak
    "CWE-532": 8,    # Log Injection / Sensitive Data in Logs
    "CWE-693": 7,    # Missing Security Header
    "CWE-770": 6,    # No Rate Limiting
    "CWE-922": 5,    # Insecure Storage

    # Low (1-4 points)
    "CWE-1104": 4,   # Unmaintained Component
    "CWE-489": 3,    # Debug Enabled
    "CWE-613": 2,    # Insufficient Session Expiration
    "CWE-1006": 1,   # Bad Coding Practice
}

_SEVERITY_WEIGHTS = {
    "critical": 20,
    "blocker": 18,
    "high": 12,
    "medium": 6,
    "low": 2,
    "info": 0,
}

# Fix complexity estimates (hours per issue type)
_FIX_EFFORT = {
    "sql_injection": 0.5,        # Parameterize query
    "hardcoded_cred": 0.25,      # Move to env/secrets
    "xss": 0.5,                  # Sanitize output
    "missing_auth": 1.0,         # Add auth decorator
    "weak_crypto": 1.0,          # Replace algorithm
    "info_leak": 0.25,           # Generic error message
    "insecure_deser": 2.0,       # Replace serializer
    "missing_fk": 0.5,           # Add constraint (per table)
    "pii_exposure": 1.0,         # Encrypt field
    "no_rate_limit": 0.5,        # Add middleware
    "missing_test": 0.25,        # Generate test stub
    "default": 1.0,
}


@dataclass
class TriagedIssue:
    """A single issue with triage metadata."""
    id: str
    title: str
    category: str
    severity: str
    cwe: str = ""
    file_path: str = ""
    line_number: int = 0
    app: str = ""
    component: str = ""
    is_pii: bool = False
    is_shared_module: bool = False
    fix_type: str = "default"
    # Computed
    priority_score: float = 0.0
    batch: int = 0                # Which remediation batch
    estimated_hours: float = 0.0
    auto_fixable: bool = False    # Can NexusForge fix automatically?


@dataclass
class TriageBatch:
    """A group of issues to fix together."""
    batch_number: int
    name: str
    issues: list[TriagedIssue] = field(default_factory=list)
    total_issues: int = 0
    estimated_hours: float = 0.0
    auto_fixable_count: int = 0
    manual_count: int = 0
    risk_reduction_pct: float = 0.0


@dataclass
class TriageReport:
    """Complete triage result."""
    total_issues: int = 0
    total_critical: int = 0
    total_auto_fixable: int = 0
    total_manual: int = 0
    estimated_total_hours: float = 0.0
    estimated_auto_hours: float = 0.0
    risk_score_before: float = 0.0
    risk_score_after: float = 0.0
    batches: list[TriageBatch] = field(default_factory=list)
    by_category: dict[str, int] = field(default_factory=dict)
    by_app: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_issues": self.total_issues,
                "critical": self.total_critical,
                "auto_fixable": self.total_auto_fixable,
                "manual_review": self.total_manual,
                "estimated_hours_total": round(self.estimated_total_hours, 1),
                "estimated_hours_auto": round(self.estimated_auto_hours, 1),
                "estimated_days_4dev": round(self.estimated_total_hours / (4 * 8), 1),
                "risk_reduction": f"{self.risk_score_before:.0f} → {self.risk_score_after:.0f}",
            },
            "by_severity": self.by_severity,
            "by_category": self.by_category,
            "by_app": dict(sorted(self.by_app.items(), key=lambda x: -x[1])[:20]),
            "batches": [
                {
                    "batch": b.batch_number,
                    "name": b.name,
                    "issues": b.total_issues,
                    "auto_fixable": b.auto_fixable_count,
                    "manual": b.manual_count,
                    "estimated_hours": round(b.estimated_hours, 1),
                    "risk_reduction": f"{b.risk_reduction_pct:.1f}%",
                    "top_issues": [
                        {"title": i.title, "file": i.file_path, "severity": i.severity, "auto": i.auto_fixable}
                        for i in b.issues[:10]
                    ],
                    "all_issues": [
                        {"title": i.title, "category": i.category, "severity": i.severity,
                         "file_path": i.file_path, "line_number": i.line_number, "app": i.app,
                         "auto_fixable": i.auto_fixable, "fix_type": i.fix_type}
                        for i in b.issues
                    ],
                }
                for b in self.batches
            ],
            "duration_ms": self.duration_ms,
        }


# ── Auto-fixable Categories ────────────────────────────────────────────────

_AUTO_FIXABLE = {
    "sql_injection",      # Parameterize queries
    "hardcoded_cred",     # Move to env vars
    "info_leak",          # Generic error message
    "weak_crypto",        # Replace MD5/SHA1
    "missing_test",       # Generate test stubs
    "no_rate_limit",      # Add rate limit decorator
}

_SHARED_MODULES = {
    "BusinessLayer", "Shared", "SharedKernel",
    "AuthService", "CommonLibrary", "Utils", "Core",
}


class IssuTriageEngine:
    """Prioritize and batch issues for remediation."""

    def triage(self, issues: list[dict], apps: list[str] | None = None) -> TriageReport:
        """Triage a list of issues into prioritized batches.

        Args:
            issues: List of dicts with keys: title, category, severity, cwe, file_path,
                    line_number, app, component
            apps: Optional filter to specific apps

        Returns:
            TriageReport with ordered batches
        """
        start = time.monotonic()
        report = TriageReport()

        # Convert to TriagedIssue and score
        triaged = []
        for i, raw in enumerate(issues):
            issue = TriagedIssue(
                id=f"ISS-{i+1:06d}",
                title=raw.get("title", ""),
                category=raw.get("category", "unknown"),
                severity=raw.get("severity", "medium"),
                cwe=raw.get("cwe", ""),
                file_path=raw.get("file_path", raw.get("file", "")),
                line_number=raw.get("line_number", raw.get("line", 0)),
                app=raw.get("app", ""),
                component=raw.get("component", ""),
            )

            # Filter by app if specified
            if apps and issue.app and issue.app not in apps:
                continue

            # Enrich
            issue.is_pii = self._check_pii(issue)
            issue.is_shared_module = self._check_shared(issue)
            issue.fix_type = self._classify_fix_type(issue)
            issue.auto_fixable = issue.fix_type in _AUTO_FIXABLE
            issue.estimated_hours = _FIX_EFFORT.get(issue.fix_type, 1.0)
            issue.priority_score = self._calculate_priority(issue)

            triaged.append(issue)

        # Sort by priority (highest first)
        triaged.sort(key=lambda x: -x.priority_score)

        # Build batches
        batches = self._build_batches(triaged)

        # Compile report
        report.total_issues = len(triaged)
        report.total_critical = sum(1 for i in triaged if i.severity in ("critical", "blocker"))
        report.total_auto_fixable = sum(1 for i in triaged if i.auto_fixable)
        report.total_manual = report.total_issues - report.total_auto_fixable
        report.estimated_total_hours = sum(i.estimated_hours for i in triaged)
        report.estimated_auto_hours = sum(i.estimated_hours for i in triaged if i.auto_fixable)
        report.batches = batches
        report.risk_score_before = sum(i.priority_score for i in triaged)
        report.risk_score_after = sum(i.priority_score for i in triaged if not i.auto_fixable) * 0.3

        # Distributions
        for i in triaged:
            report.by_category[i.category] = report.by_category.get(i.category, 0) + 1
            report.by_app[i.app or "unknown"] = report.by_app.get(i.app or "unknown", 0) + 1
            report.by_severity[i.severity] = report.by_severity.get(i.severity, 0) + 1

        report.duration_ms = int((time.monotonic() - start) * 1000)
        return report

    def _calculate_priority(self, issue: TriagedIssue) -> float:
        """Calculate priority score (higher = fix first)."""
        score = 0.0

        # Base: severity weight
        score += _SEVERITY_WEIGHTS.get(issue.severity, 5)

        # CWE-specific weight
        if issue.cwe:
            score += _CWE_WEIGHTS.get(issue.cwe, 5)

        # Category boost
        category_boost = {
            "sql_injection": 15,
            "hardcoded_cred": 12,
            "command_injection": 14,
            "insecure_deser": 13,
            "pii_exposure": 11,
            "xss": 8,
            "missing_auth": 7,
            "weak_crypto": 5,
            "info_leak": 3,
        }
        score += category_boost.get(issue.category, 0)

        # PII multiplier
        if issue.is_pii:
            score *= 1.5

        # Shared module multiplier (higher blast radius)
        if issue.is_shared_module:
            score *= 1.3

        # Easy win bonus (auto-fixable get slight boost within same tier)
        if issue.auto_fixable:
            score += 2

        return round(score, 2)

    def _check_pii(self, issue: TriagedIssue) -> bool:
        """Check if issue involves personal data."""
        pii_keywords = [
            "personal", "pii", "email", "phone", "address", "name", "passport",
            "credit_card", "card_number", "ssn", "tax_id", "national_id",
            "customer", "client", "subscriber", "birth", "gender",
        ]
        text = f"{issue.title} {issue.file_path} {issue.component}".lower()
        return any(kw in text for kw in pii_keywords)

    def _check_shared(self, issue: TriagedIssue) -> bool:
        """Check if issue is in a shared/cross-module component."""
        text = f"{issue.file_path} {issue.component} {issue.app}"
        return any(mod.lower() in text.lower() for mod in _SHARED_MODULES)

    def _classify_fix_type(self, issue: TriagedIssue) -> str:
        """Classify the type of fix needed."""
        cat = issue.category.lower()
        title = issue.title.lower()

        if "sql" in cat or "sql injection" in title or "concatenat" in title:
            return "sql_injection"
        if "credential" in cat or "hardcoded" in title or "password" in title:
            return "hardcoded_cred"
        if "xss" in cat or "cross-site" in title:
            return "xss"
        if "auth" in cat or "authorize" in title:
            return "missing_auth"
        if "crypto" in cat or "md5" in title or "sha1" in title:
            return "weak_crypto"
        if "leak" in cat or "exception" in title or "stack trace" in title:
            return "info_leak"
        if "deserial" in cat or "binaryformatter" in title:
            return "insecure_deser"
        if "foreign key" in title or "fk" in cat:
            return "missing_fk"
        if "pii" in cat or "personal data" in title:
            return "pii_exposure"
        if "rate" in cat or "throttl" in title:
            return "no_rate_limit"
        if "test" in cat:
            return "missing_test"
        return "default"

    def _build_batches(self, triaged: list[TriagedIssue]) -> list[TriageBatch]:
        """Group issues into remediation batches."""
        batches = []
        total_risk = sum(i.priority_score for i in triaged) or 1

        # Batch 1: Critical SQL injections (auto-fixable, highest impact)
        b1_issues = [i for i in triaged if i.fix_type == "sql_injection" and i.severity in ("critical", "blocker")]
        if b1_issues:
            for i in b1_issues:
                i.batch = 1
            batches.append(self._make_batch(1, "Critical SQL Injection Remediation", b1_issues, total_risk))

        # Batch 2: Hardcoded credentials (auto-fixable, quick wins)
        b2_issues = [i for i in triaged if i.fix_type == "hardcoded_cred" and i.batch == 0]
        if b2_issues:
            for i in b2_issues:
                i.batch = 2
            batches.append(self._make_batch(2, "Credential Extraction → Secrets Manager", b2_issues, total_risk))

        # Batch 3: PII exposure (regulatory requirement)
        b3_issues = [i for i in triaged if i.is_pii and i.batch == 0]
        if b3_issues:
            for i in b3_issues:
                i.batch = 3
            batches.append(self._make_batch(3, "Personal Data Protection (Regulatory)", b3_issues, total_risk))

        # Batch 4: Remaining critical/blocker
        b4_issues = [i for i in triaged if i.severity in ("critical", "blocker") and i.batch == 0]
        if b4_issues:
            for i in b4_issues:
                i.batch = 4
            batches.append(self._make_batch(4, "Remaining Critical/Blocker Issues", b4_issues, total_risk))

        # Batch 5: High severity auto-fixable
        b5_issues = [i for i in triaged if i.severity == "high" and i.auto_fixable and i.batch == 0]
        if b5_issues:
            for i in b5_issues:
                i.batch = 5
            batches.append(self._make_batch(5, "High Severity — Auto-Fixable", b5_issues, total_risk))

        # Batch 6: Shared module issues (high blast radius)
        b6_issues = [i for i in triaged if i.is_shared_module and i.batch == 0]
        if b6_issues:
            for i in b6_issues:
                i.batch = 6
            batches.append(self._make_batch(6, "Shared Module Remediation (High Blast Radius)", b6_issues, total_risk))

        # Batch 7: Everything else
        b7_issues = [i for i in triaged if i.batch == 0]
        if b7_issues:
            for i in b7_issues:
                i.batch = 7
            batches.append(self._make_batch(7, "Medium/Low Priority — Remaining Issues", b7_issues, total_risk))

        return batches

    def _make_batch(self, num: int, name: str, issues: list[TriagedIssue], total_risk: float) -> TriageBatch:
        batch = TriageBatch(
            batch_number=num,
            name=name,
            issues=issues,
            total_issues=len(issues),
            estimated_hours=sum(i.estimated_hours for i in issues),
            auto_fixable_count=sum(1 for i in issues if i.auto_fixable),
            manual_count=sum(1 for i in issues if not i.auto_fixable),
            risk_reduction_pct=(sum(i.priority_score for i in issues) / total_risk) * 100,
        )
        return batch
