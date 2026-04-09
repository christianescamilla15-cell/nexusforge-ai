"""Database Integrity Analyzer — detect missing FK, PII exposure, schema issues.

Designed for Aeromexico-scale databases:
  - 97% of tables missing foreign keys
  - 15-20% monthly growth with no archiving
  - 25 types of personal data across 318 inputs
  - Multiple DB engines: SQL Server, Aurora MySQL, DB2, Oracle

Analysis modes:
  1. SCHEMA SCAN: Parse SQL migration files, DDL scripts, or connect to live DB
  2. CODE SCAN: Analyze source code for DB interactions (connection strings, queries)
  3. PII DETECTION: Find personal data in column names, queries, and models

Output: Integrity report with FK proposals, PII map, and archiving recommendations.
"""

import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── PII Patterns ───────────────────────────────────────────────────────────

_PII_COLUMN_PATTERNS = {
    # Direct identifiers
    "name": ["first_name", "last_name", "full_name", "nombre", "apellido", "passenger_name", "customer_name"],
    "email": ["email", "correo", "e_mail", "email_address"],
    "phone": ["phone", "telefono", "mobile", "celular", "phone_number"],
    "address": ["address", "direccion", "street", "calle", "city", "ciudad", "zip", "postal"],
    "national_id": ["rfc", "curp", "ssn", "social_security", "cedula", "passport", "pasaporte"],
    "financial": ["credit_card", "card_number", "tarjeta", "cuenta", "account_number", "cvv", "expiry"],
    "travel": ["pnr", "booking_ref", "ticket_number", "boleto", "reservation", "itinerary"],
    "biometric": ["fingerprint", "huella", "face_id", "photo", "foto"],
    "demographic": ["birth_date", "fecha_nacimiento", "gender", "genero", "age", "edad", "nationality"],
    "auth": ["password", "pwd", "token", "secret", "api_key", "hash", "salt"],
}

_PII_REGEX_PATTERNS = [
    (r"(?i)\b(?:first|last|full)[-_]?name\b", "name", "high"),
    (r"(?i)\b(?:email|correo|e[-_]mail)\b", "email", "high"),
    (r"(?i)\b(?:phone|telefono|mobile|celular)\b", "phone", "high"),
    (r"(?i)\b(?:rfc|curp|ssn|passport|pasaporte)\b", "national_id", "critical"),
    (r"(?i)\b(?:credit[-_]?card|card[-_]?number|tarjeta|cvv)\b", "financial", "critical"),
    (r"(?i)\b(?:pnr|booking[-_]?ref|ticket[-_]?num)\b", "travel", "high"),
    (r"(?i)\b(?:password|pwd|secret|api[-_]?key)\b", "auth", "critical"),
    (r"(?i)\b(?:birth[-_]?date|fecha[-_]?nac|gender|genero)\b", "demographic", "medium"),
    (r"(?i)\b(?:address|direccion|street|calle|zip|postal)\b", "address", "medium"),
]


@dataclass
class TableInfo:
    name: str
    schema: str = "dbo"
    columns: list[dict] = field(default_factory=list)   # [{name, type, nullable, pk}]
    primary_key: list[str] = field(default_factory=list)
    foreign_keys: list[dict] = field(default_factory=list)  # [{column, ref_table, ref_column}]
    indexes: list[str] = field(default_factory=list)
    row_estimate: int = 0
    pii_columns: list[dict] = field(default_factory=list)   # [{column, pii_type, severity}]
    has_timestamp: bool = False     # Has created_at/updated_at
    has_soft_delete: bool = False   # Has is_deleted/deleted_at


@dataclass
class FKProposal:
    table: str
    column: str
    ref_table: str
    ref_column: str
    confidence: float = 0.0    # 0-1 how confident the match is
    sql: str = ""              # ALTER TABLE ADD CONSTRAINT statement


@dataclass
class DBIntegrityReport:
    total_tables: int = 0
    tables_with_fk: int = 0
    tables_without_fk: int = 0
    fk_coverage_pct: float = 0.0
    total_pii_columns: int = 0
    pii_by_type: dict[str, int] = field(default_factory=dict)
    pii_critical: int = 0
    fk_proposals: list[FKProposal] = field(default_factory=list)
    tables_needing_archive: list[dict] = field(default_factory=list)
    tables_missing_timestamps: list[str] = field(default_factory=list)
    tables_missing_soft_delete: list[str] = field(default_factory=list)
    connection_strings_found: list[dict] = field(default_factory=list)
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_tables": self.total_tables,
                "with_fk": self.tables_with_fk,
                "without_fk": self.tables_without_fk,
                "fk_coverage": f"{self.fk_coverage_pct:.1f}%",
                "pii_columns": self.total_pii_columns,
                "pii_critical": self.pii_critical,
                "fk_proposals": len(self.fk_proposals),
                "tables_need_archiving": len(self.tables_needing_archive),
            },
            "pii_by_type": self.pii_by_type,
            "fk_proposals": [
                {
                    "table": p.table,
                    "column": p.column,
                    "references": f"{p.ref_table}.{p.ref_column}",
                    "confidence": f"{p.confidence:.0%}",
                    "sql": p.sql,
                }
                for p in sorted(self.fk_proposals, key=lambda x: -x.confidence)[:50]
            ],
            "tables_needing_archive": self.tables_needing_archive[:20],
            "tables_missing_timestamps": self.tables_missing_timestamps[:20],
            "connection_strings": len(self.connection_strings_found),
            "duration_ms": self.duration_ms,
        }


class DatabaseIntegrityAnalyzer:
    """Analyze database schema for integrity, PII, and archiving issues."""

    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.tables: dict[str, TableInfo] = {}

    async def analyze(self) -> DBIntegrityReport:
        """Full database integrity analysis from source code."""
        start = time.monotonic()
        report = DBIntegrityReport()

        # Phase 1: Extract table definitions from SQL files
        self._scan_sql_files()

        # Phase 2: Extract table definitions from C#/Python models
        self._scan_model_files()

        # Phase 3: Extract from migration files
        self._scan_migrations()

        # Phase 4: Detect PII in all tables
        self._detect_pii()

        # Phase 5: Propose foreign keys
        fk_proposals = self._propose_fks()

        # Phase 6: Detect archiving needs
        archive_candidates = self._detect_archive_needs()

        # Phase 7: Find connection strings
        conn_strings = self._scan_connection_strings()

        # Compile report
        report.total_tables = len(self.tables)
        report.tables_with_fk = sum(1 for t in self.tables.values() if t.foreign_keys)
        report.tables_without_fk = report.total_tables - report.tables_with_fk
        report.fk_coverage_pct = (report.tables_with_fk / max(report.total_tables, 1)) * 100

        for t in self.tables.values():
            for pii in t.pii_columns:
                report.total_pii_columns += 1
                pii_type = pii["pii_type"]
                report.pii_by_type[pii_type] = report.pii_by_type.get(pii_type, 0) + 1
                if pii["severity"] == "critical":
                    report.pii_critical += 1

            if not t.has_timestamp:
                report.tables_missing_timestamps.append(t.name)
            if not t.has_soft_delete:
                report.tables_missing_soft_delete.append(t.name)

        report.fk_proposals = fk_proposals
        report.tables_needing_archive = archive_candidates
        report.connection_strings_found = conn_strings
        report.duration_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "DB analysis: %d tables, %d%% FK coverage, %d PII columns, %d FK proposals in %dms",
            report.total_tables, report.fk_coverage_pct,
            report.total_pii_columns, len(report.fk_proposals),
            report.duration_ms,
        )
        return report

    def _scan_sql_files(self):
        """Parse .sql files for CREATE TABLE statements."""
        for fpath in self.root.rglob("*.sql"):
            if any(skip in str(fpath) for skip in ["node_modules", "__pycache__", ".git"]):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                self._parse_create_tables(content)
            except Exception:
                pass

    def _scan_model_files(self):
        """Extract table info from C# Entity classes and Python models."""
        # C# Entity Framework models
        for fpath in self.root.rglob("*.cs"):
            if any(skip in str(fpath) for skip in ["bin/", "obj/", "node_modules"]):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                self._parse_csharp_models(content)
            except Exception:
                pass

        # Python SQLAlchemy models
        for fpath in self.root.rglob("*.py"):
            if "__pycache__" in str(fpath):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                self._parse_python_models(content)
            except Exception:
                pass

    def _scan_migrations(self):
        """Parse migration files."""
        for pattern in ["**/migrations/*.sql", "**/Migrations/*.cs", "**/db/migrations/*.sql"]:
            for fpath in self.root.glob(pattern):
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    self._parse_create_tables(content)
                except Exception:
                    pass

    def _parse_create_tables(self, sql: str):
        """Extract table definitions from SQL CREATE TABLE statements."""
        for m in re.finditer(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\[?(\w+)\]?\.)?\[?(\w+)\]?\s*\((.*?)\)',
            sql, re.IGNORECASE | re.DOTALL
        ):
            schema = m.group(1) or "dbo"
            table_name = m.group(2)
            body = m.group(3)

            if table_name.startswith("_") or table_name.startswith("#"):
                continue

            table = self.tables.get(table_name, TableInfo(name=table_name, schema=schema))

            # Extract columns
            for col_match in re.finditer(
                r'\[?(\w+)\]?\s+([\w()]+(?:\(\d+(?:,\s*\d+)?\))?)',
                body
            ):
                col_name = col_match.group(1)
                col_type = col_match.group(2)
                if col_name.upper() in ("PRIMARY", "FOREIGN", "CONSTRAINT", "INDEX", "UNIQUE", "CHECK"):
                    continue
                table.columns.append({
                    "name": col_name,
                    "type": col_type,
                    "nullable": "NOT NULL" not in body[col_match.start():col_match.end() + 30],
                })

                # Check for timestamps
                if col_name.lower() in ("created_at", "createdat", "created_date", "fecha_creacion"):
                    table.has_timestamp = True
                if col_name.lower() in ("deleted_at", "deletedat", "is_deleted", "isdeleted"):
                    table.has_soft_delete = True

            # Extract primary key
            pk_match = re.search(r'PRIMARY\s+KEY\s*\(([^)]+)\)', body, re.IGNORECASE)
            if pk_match:
                table.primary_key = [c.strip().strip("[]") for c in pk_match.group(1).split(",")]

            # Extract foreign keys
            for fk_match in re.finditer(
                r'FOREIGN\s+KEY\s*\(\[?(\w+)\]?\)\s*REFERENCES\s+\[?(?:(\w+)\.)?\]?\[?(\w+)\]?\s*\(\[?(\w+)\]?\)',
                body, re.IGNORECASE
            ):
                table.foreign_keys.append({
                    "column": fk_match.group(1),
                    "ref_table": fk_match.group(3),
                    "ref_column": fk_match.group(4),
                })

            self.tables[table_name] = table

    def _parse_csharp_models(self, content: str):
        """Extract table info from C# Entity Framework models."""
        for m in re.finditer(
            r'\[Table\("(\w+)"\)\]\s*(?:public\s+)?class\s+(\w+)',
            content
        ):
            table_name = m.group(1)
            table = self.tables.get(table_name, TableInfo(name=table_name))

            # Extract properties as columns
            for prop in re.finditer(
                r'public\s+([\w<>?]+)\s+(\w+)\s*\{',
                content[m.end():m.end() + 3000]
            ):
                prop_type = prop.group(1)
                prop_name = prop.group(2)
                if prop_name in ("class", "void"):
                    continue
                table.columns.append({"name": prop_name, "type": prop_type, "nullable": "?" in prop_type})

            self.tables[table_name] = table

    def _parse_python_models(self, content: str):
        """Extract table info from SQLAlchemy models."""
        for m in re.finditer(
            r'__tablename__\s*=\s*["\'](\w+)["\']',
            content
        ):
            table_name = m.group(1)
            table = self.tables.get(table_name, TableInfo(name=table_name))

            # Extract Column definitions
            for col in re.finditer(
                r'(\w+)\s*=\s*(?:db\.)?Column\(\s*(?:db\.)?(\w+)',
                content[m.start():m.start() + 3000]
            ):
                table.columns.append({"name": col.group(1), "type": col.group(2), "nullable": True})

            # Extract ForeignKey
            for fk in re.finditer(
                r'(\w+)\s*=\s*(?:db\.)?Column\(.*ForeignKey\(["\'](\w+)\.(\w+)["\']\)',
                content[m.start():m.start() + 3000]
            ):
                table.foreign_keys.append({
                    "column": fk.group(1),
                    "ref_table": fk.group(2),
                    "ref_column": fk.group(3),
                })

            self.tables[table_name] = table

    def _detect_pii(self):
        """Detect PII in column names."""
        for table in self.tables.values():
            for col in table.columns:
                col_name = col["name"].lower()
                for pattern, pii_type, severity in _PII_REGEX_PATTERNS:
                    if re.search(pattern, col_name):
                        table.pii_columns.append({
                            "column": col["name"],
                            "pii_type": pii_type,
                            "severity": severity,
                        })
                        break

    def _propose_fks(self) -> list[FKProposal]:
        """Propose foreign key constraints based on naming conventions."""
        proposals = []
        table_names = set(self.tables.keys())
        table_names_lower = {t.lower(): t for t in table_names}

        for table in self.tables.values():
            if table.foreign_keys:
                continue  # Already has FKs

            for col in table.columns:
                col_name = col["name"].lower()

                # Pattern: column ends with _id and matches a table name
                if col_name.endswith("_id") or col_name.endswith("id"):
                    base = col_name.replace("_id", "").replace("id", "")
                    if not base:
                        continue

                    # Try to match: users_id → users, user_id → users/user
                    candidates = []
                    for tname_lower, tname in table_names_lower.items():
                        if tname == table.name:
                            continue
                        if base == tname_lower or base + "s" == tname_lower or base == tname_lower.rstrip("s"):
                            candidates.append((tname, 0.9))
                        elif base in tname_lower:
                            candidates.append((tname, 0.6))

                    for ref_table, confidence in candidates:
                        ref = self.tables.get(ref_table)
                        ref_col = "id"
                        if ref and ref.primary_key:
                            ref_col = ref.primary_key[0]

                        sql = (
                            f"ALTER TABLE [{table.schema}].[{table.name}] "
                            f"ADD CONSTRAINT FK_{table.name}_{col['name']} "
                            f"FOREIGN KEY ([{col['name']}]) REFERENCES [{ref_table}]([{ref_col}]);"
                        )
                        proposals.append(FKProposal(
                            table=table.name,
                            column=col["name"],
                            ref_table=ref_table,
                            ref_column=ref_col,
                            confidence=confidence,
                            sql=sql,
                        ))

        return proposals

    def _detect_archive_needs(self) -> list[dict]:
        """Identify tables that likely need archiving strategy."""
        candidates = []
        archive_keywords = ["log", "audit", "history", "event", "transaction", "session", "temp", "cache"]

        for table in self.tables.values():
            name_lower = table.name.lower()
            if any(kw in name_lower for kw in archive_keywords):
                candidates.append({
                    "table": table.name,
                    "reason": "Name suggests temporal/log data",
                    "has_timestamp": table.has_timestamp,
                    "recommendation": "Add partition by date + archive policy (30/90/365 days)",
                })
            elif table.has_timestamp and len(table.columns) > 3:
                # Tables with timestamps and many columns = likely growing
                candidates.append({
                    "table": table.name,
                    "reason": "Has timestamp columns, likely accumulating data",
                    "has_timestamp": True,
                    "recommendation": "Monitor growth, add archiving if > 1M rows",
                })

        return candidates

    def _scan_connection_strings(self) -> list[dict]:
        """Find connection strings in code."""
        results = []
        patterns = [
            (r'(?i)(?:Server|Data Source)\s*=\s*([^;"\s]+)', "sql_server"),
            (r'(?i)mysql://([^"\'>\s]+)', "mysql"),
            (r'(?i)postgres(?:ql)?://([^"\'>\s]+)', "postgresql"),
            (r'(?i)(?:Provider\s*=\s*IBMDADB2|Database\s*=\s*\w+.*(?:DB2|AS400))', "db2"),
        ]

        for fpath in self.root.rglob("*"):
            if not fpath.is_file() or fpath.suffix not in (".cs", ".py", ".config", ".json", ".xml", ".yml", ".yaml"):
                continue
            if any(skip in str(fpath) for skip in ["node_modules", "__pycache__", ".git", "bin/", "obj/"]):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                rel = str(fpath.relative_to(self.root))
                for pattern, db_type in patterns:
                    if re.search(pattern, content):
                        results.append({"file": rel, "db_type": db_type})
                        break
            except Exception:
                pass

        return results
