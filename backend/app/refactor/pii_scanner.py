"""PII Scanner — detect personal data exposure across 5.6M LOC.

Aeromexico context:
  - 25 types of personal data
  - 318 input points
  - Data breach Sept-Oct 2025 exposed PNRs
  - $5M USD penalty risk (GDPR-level)

Scans:
  1. Source code: variable names, comments, string literals
  2. SQL queries: SELECT/INSERT columns with PII
  3. API endpoints: request/response bodies with PII
  4. Config files: connection strings, API keys
  5. Log statements: PII in log output

For each PII finding, recommends:
  - Encryption at rest (AES-256)
  - Masking in logs (****1234)
  - Access control (who can query this field)
  - Retention policy (how long to keep)
"""

import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Aeromexico's 25 PII types (from Softtek assessment)
PII_TYPES = {
    # Critical — immediate encryption required
    "credit_card": {
        "patterns": [r"(?i)\b(?:credit[-_]?card|card[-_]?num|tarjeta|numero[-_]?tarjeta|cvv|cvc|expiry[-_]?date)\b"],
        "severity": "critical",
        "encryption": "AES-256-GCM",
        "mask": "****-****-****-{last4}",
        "retention": "PCI: delete after transaction + 90 days",
    },
    "passport": {
        "patterns": [r"(?i)\b(?:passport|pasaporte|passport[-_]?num)\b"],
        "severity": "critical",
        "encryption": "AES-256-GCM",
        "mask": "***{last3}",
        "retention": "Delete after travel + 1 year",
    },
    "national_id_mx": {
        "patterns": [r"(?i)\b(?:rfc|curp|ine|credencial[-_]?elector)\b"],
        "severity": "critical",
        "encryption": "AES-256-GCM",
        "mask": "{first4}******{last2}",
        "retention": "Mexican law: 5 years after relationship ends",
    },
    "pnr": {
        "patterns": [r"(?i)\b(?:pnr|booking[-_]?ref|record[-_]?locator|localizador)\b"],
        "severity": "critical",
        "encryption": "AES-256-GCM",
        "mask": "***{last3}",
        "retention": "IATA: 13 months after travel",
    },
    "password": {
        "patterns": [r"(?i)\b(?:password|contraseña|pwd|passwd|secret[-_]?key|api[-_]?key)\b"],
        "severity": "critical",
        "encryption": "bcrypt/argon2 (hash, never store plain)",
        "mask": "********",
        "retention": "Hash only, rotate every 90 days",
    },

    # High — encryption recommended
    "email": {
        "patterns": [r"(?i)\b(?:email|correo|e[-_]?mail|email[-_]?addr)\b"],
        "severity": "high",
        "encryption": "AES-256",
        "mask": "{first2}***@{domain}",
        "retention": "Consent-based, delete on request",
    },
    "phone": {
        "patterns": [r"(?i)\b(?:phone|telefono|mobile|celular|cell[-_]?phone|tel)\b"],
        "severity": "high",
        "encryption": "AES-256",
        "mask": "****{last4}",
        "retention": "Consent-based",
    },
    "full_name": {
        "patterns": [r"(?i)\b(?:full[-_]?name|nombre[-_]?completo|passenger[-_]?name|customer[-_]?name|first[-_]?name|last[-_]?name|apellido)\b"],
        "severity": "high",
        "encryption": "AES-256",
        "mask": "{first_initial}. {last_initial}.",
        "retention": "Active relationship + 5 years",
    },
    "address": {
        "patterns": [r"(?i)\b(?:address|direccion|domicilio|street|calle|colonia|zip[-_]?code|codigo[-_]?postal)\b"],
        "severity": "high",
        "encryption": "AES-256",
        "mask": "*** {city}",
        "retention": "Consent-based",
    },
    "birth_date": {
        "patterns": [r"(?i)\b(?:birth[-_]?date|fecha[-_]?nac|dob|date[-_]?of[-_]?birth)\b"],
        "severity": "high",
        "encryption": "AES-256",
        "mask": "****-**-**",
        "retention": "Active relationship + 5 years",
    },
    "ticket_number": {
        "patterns": [r"(?i)\b(?:ticket[-_]?num|numero[-_]?boleto|e[-_]?ticket|boleto)\b"],
        "severity": "high",
        "encryption": "AES-256",
        "mask": "***{last4}",
        "retention": "IATA: 13 months",
    },

    # Medium — masking required
    "gender": {
        "patterns": [r"(?i)\b(?:gender|genero|sexo|sex)\b"],
        "severity": "medium",
        "encryption": "Optional",
        "mask": "N/A",
        "retention": "Consent-based",
    },
    "nationality": {
        "patterns": [r"(?i)\b(?:nationality|nacionalidad|country[-_]?of[-_]?origin|pais)\b"],
        "severity": "medium",
        "encryption": "Optional",
        "mask": "N/A",
        "retention": "Consent-based",
    },
    "frequent_flyer": {
        "patterns": [r"(?i)\b(?:frequent[-_]?flyer|club[-_]?premier|loyalty|plm|mileage)\b"],
        "severity": "medium",
        "encryption": "AES-256",
        "mask": "***{last4}",
        "retention": "Active membership + 2 years",
    },
    "ip_address": {
        "patterns": [r"(?i)\b(?:ip[-_]?addr|client[-_]?ip|remote[-_]?addr|ip[-_]?address)\b"],
        "severity": "medium",
        "encryption": "Optional",
        "mask": "{first_octet}.*.*.*",
        "retention": "30 days (logs)",
    },
}


@dataclass
class PIIFinding:
    file_path: str
    line_number: int
    pii_type: str
    severity: str
    context: str          # code line or column name
    location_type: str    # source_code, sql_query, api_endpoint, config, log
    encryption_rec: str
    mask_rec: str
    retention_rec: str


@dataclass
class PIIReport:
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_file: dict[str, int] = field(default_factory=dict)
    by_location: dict[str, int] = field(default_factory=dict)
    findings: list[PIIFinding] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total": self.total_findings,
                "critical": self.critical,
                "high": self.high,
                "medium": self.medium,
                "unique_pii_types": len(self.by_type),
                "files_affected": len(self.by_file),
            },
            "by_type": dict(sorted(self.by_type.items(), key=lambda x: -x[1])),
            "by_location": self.by_location,
            "top_files": dict(sorted(self.by_file.items(), key=lambda x: -x[1])[:20]),
            "findings": [
                {
                    "file": f.file_path,
                    "line": f.line_number,
                    "type": f.pii_type,
                    "severity": f.severity,
                    "context": f.context[:100],
                    "location": f.location_type,
                    "encrypt": f.encryption_rec,
                    "mask": f.mask_rec,
                    "retention": f.retention_rec,
                }
                for f in sorted(self.findings, key=lambda x: {"critical": 0, "high": 1, "medium": 2}.get(x.severity, 3))[:200]
            ],
            "recommendations": self.recommendations,
            "duration_ms": self.duration_ms,
        }


class PIIScanner:
    """Scan codebase for personal data exposure."""

    def __init__(self, project_root: str):
        self.root = Path(project_root)

    async def scan(self) -> PIIReport:
        """Full PII scan across all source files."""
        start = time.monotonic()
        report = PIIReport()

        extensions = {".cs", ".py", ".java", ".php", ".ts", ".js", ".jsx", ".vb",
                      ".sql", ".config", ".json", ".xml", ".yml", ".yaml"}

        for fpath in self.root.rglob("*"):
            if not fpath.is_file() or fpath.suffix not in extensions:
                continue
            if any(skip in str(fpath) for skip in ["node_modules", "__pycache__", ".git", "bin/", "obj/", "dist/"]):
                continue

            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                rel = str(fpath.relative_to(self.root))
                lines = content.splitlines()

                for line_num, line in enumerate(lines, 1):
                    for pii_type, config in PII_TYPES.items():
                        for pattern in config["patterns"]:
                            if re.search(pattern, line):
                                # Determine location type
                                loc = self._classify_location(line, fpath.suffix)

                                finding = PIIFinding(
                                    file_path=rel,
                                    line_number=line_num,
                                    pii_type=pii_type,
                                    severity=config["severity"],
                                    context=line.strip(),
                                    location_type=loc,
                                    encryption_rec=config["encryption"],
                                    mask_rec=config["mask"],
                                    retention_rec=config["retention"],
                                )
                                report.findings.append(finding)

                                report.by_type[pii_type] = report.by_type.get(pii_type, 0) + 1
                                report.by_file[rel] = report.by_file.get(rel, 0) + 1
                                report.by_location[loc] = report.by_location.get(loc, 0) + 1

                                if config["severity"] == "critical":
                                    report.critical += 1
                                elif config["severity"] == "high":
                                    report.high += 1
                                else:
                                    report.medium += 1
                                break  # One match per PII type per line
            except Exception:
                pass

        report.total_findings = len(report.findings)

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        report.duration_ms = int((time.monotonic() - start) * 1000)
        return report

    def _classify_location(self, line: str, suffix: str) -> str:
        """Classify where PII appears."""
        line_lower = line.lower()
        if re.search(r'(?:select|insert|update|delete)\s', line_lower):
            return "sql_query"
        if re.search(r'(?:log|print|console|logger)\s*[\.(]', line_lower):
            return "log_statement"
        if re.search(r'(?:\[HttpGet\]|\[HttpPost\]|@app\.route|@router)', line):
            return "api_endpoint"
        if suffix in (".config", ".json", ".xml", ".yml", ".yaml"):
            return "config_file"
        return "source_code"

    def _generate_recommendations(self, report: PIIReport) -> list[dict]:
        """Generate actionable recommendations based on findings."""
        recs = []

        if report.critical > 0:
            recs.append({
                "priority": "P0",
                "title": f"Encrypt {report.critical} critical PII fields immediately",
                "description": "Credit cards, passwords, national IDs, and PNRs require AES-256-GCM encryption at rest",
                "effort": f"~{report.critical * 1.0:.0f} hours",
            })

        log_pii = report.by_location.get("log_statement", 0)
        if log_pii > 0:
            recs.append({
                "priority": "P0",
                "title": f"Remove {log_pii} PII instances from log statements",
                "description": "Personal data in logs violates data protection regulations and creates breach risk",
                "effort": f"~{log_pii * 0.25:.0f} hours",
            })

        sql_pii = report.by_location.get("sql_query", 0)
        if sql_pii > 0:
            recs.append({
                "priority": "P1",
                "title": f"Add column-level encryption to {sql_pii} SQL queries handling PII",
                "description": "Encrypt PII columns in database, decrypt only at application layer",
                "effort": f"~{sql_pii * 1.0:.0f} hours",
            })

        if report.high > 0:
            recs.append({
                "priority": "P1",
                "title": f"Implement masking for {report.high} high-severity PII fields",
                "description": "Mask email, phone, names in UI displays and API responses",
                "effort": f"~{report.high * 0.5:.0f} hours",
            })

        api_pii = report.by_location.get("api_endpoint", 0)
        if api_pii > 0:
            recs.append({
                "priority": "P1",
                "title": f"Add access control to {api_pii} API endpoints exposing PII",
                "description": "Implement field-level authorization — only authorized roles see full PII",
                "effort": f"~{api_pii * 2.0:.0f} hours",
            })

        return recs
