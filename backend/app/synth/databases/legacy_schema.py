"""Legacy SQL schema fixture generator.

Emits a ``schema.sql`` file that looks like a real enterprise legacy
database dump circa 2012: many tables, no foreign keys, nullable columns
everywhere, stored procedures with stale comments, PII columns stored in
plaintext.

The output is intentionally compatible with NexusForge's
``backend/app/refactor/db_analyzer.py`` so the integrity analyzer picks
up the missing-FK and PII-column signals.

Usage:
    from app.synth.databases import generate_legacy_schema
    generate_legacy_schema(app_recipe, rng, out_dir)
"""
from __future__ import annotations

import random
from pathlib import Path

from ..profile import AppRecipe


# ── Table name vocabularies (domain-neutral) ───────────────────────────────

_BUSINESS_NOUNS = [
    "transaction", "document", "record", "entity", "reference", "catalog",
    "parameter", "config", "ledger", "entry", "batch", "reconciliation",
    "period", "calendar", "holiday", "exchange_rate", "tax", "fee",
    "discount", "promotion", "campaign", "charge", "adjustment", "refund",
    "credit", "debit", "invoice", "bill", "statement", "report", "summary",
    "audit", "log", "event", "notification", "message", "alert",
    "user", "role", "permission", "group", "account", "profile", "session",
    "contact", "address", "phone", "email_record", "preference",
]

_PII_COLUMN_NAMES = [
    ("customer_name", "VARCHAR(200)"),
    ("full_name", "VARCHAR(200)"),
    ("email_address", "VARCHAR(255)"),
    ("phone_number", "VARCHAR(40)"),
    ("birth_date", "DATE"),
    ("national_id", "VARCHAR(40)"),
    ("tax_id", "VARCHAR(40)"),
    ("credit_card_num", "VARCHAR(20)"),
    ("street_address", "VARCHAR(255)"),
    ("postal_code", "VARCHAR(20)"),
    ("transaction_reference", "VARCHAR(40)"),
    ("password", "VARCHAR(255)"),
]

_NORMAL_COLUMNS = [
    ("status", "VARCHAR(20)"),
    ("amount", "DECIMAL(18,2)"),
    ("quantity", "INT"),
    ("code", "VARCHAR(50)"),
    ("description", "VARCHAR(500)"),
    ("notes", "TEXT"),
    ("is_active", "TINYINT"),
    ("sort_order", "INT"),
    ("version_num", "INT"),
]

_LEGACY_COMMENTS = [
    "-- last modified 2011-08-14 (imported from predecessor system)",
    "-- modified 2012-03-15 (reconciliation rewrite, pre-cloud era)",
    "-- last touched 2013-01-07 (bugfix sprint)",
    "-- original schema: 2009. Current version: 2012.",
    "-- DO NOT ADD FOREIGN KEYS — application enforces referential integrity",
    "-- TODO(2014): extract to separate schema",
    "-- schema stable since 2012; see wiki for history",
]

_STORED_PROC_STUBS = [
    "    -- Legacy batch reconciliation logic, unchanged since 2012.\n"
    "    -- No transaction boundaries — callers must wrap explicitly.\n"
    "    SELECT * FROM {table} WHERE period_id = @period_id;\n"
    "    UPDATE {table} SET status = 'processed' WHERE period_id = @period_id;",

    "    -- Original author left the team in 2014; logic is opaque.\n"
    "    -- Change only with full regression pass.\n"
    "    DECLARE @total DECIMAL(18,2);\n"
    "    SELECT @total = SUM(amount) FROM {table} WHERE created_at >= @since;\n"
    "    RETURN @total;",

    "    -- Copy-paste from {other}; kept separate for audit trail.\n"
    "    -- Last review: 2013.\n"
    "    INSERT INTO {table}_audit SELECT *, GETDATE() FROM {table};\n"
    "    DELETE FROM {table} WHERE is_active = 0;",
]


# ── Schema generator ───────────────────────────────────────────────────────


def _make_table_name(rng: random.Random, used: set[str]) -> str:
    for _ in range(200):
        parts = rng.sample(_BUSINESS_NOUNS, 2)
        name = f"tbl_{parts[0]}_{parts[1]}"
        if name not in used:
            used.add(name)
            return name
    # Fallback if we somehow collide 200 times in a row
    for i in range(1_000):
        name = f"tbl_legacy_{i:04d}"
        if name not in used:
            used.add(name)
            return name
    return f"tbl_legacy_{rng.randint(10_000, 99_999)}"


def _render_table(
    rng: random.Random,
    name: str,
    has_pii: bool,
    comment: str,
) -> str:
    """Render one CREATE TABLE statement with no foreign keys and many nulls."""
    columns: list[str] = [
        f"    id INT NOT NULL,"  # No PK — deliberately.
    ]

    # Business columns (nullable on purpose — typical legacy anti-pattern)
    normal_count = rng.randint(4, 9)
    for col, dtype in rng.sample(_NORMAL_COLUMNS, min(normal_count, len(_NORMAL_COLUMNS))):
        columns.append(f"    {col} {dtype} NULL,")

    # PII columns — plaintext, no encryption
    if has_pii:
        pii_count = rng.randint(2, 5)
        for col, dtype in rng.sample(_PII_COLUMN_NAMES, min(pii_count, len(_PII_COLUMN_NAMES))):
            columns.append(f"    {col} {dtype} NULL,  -- PII (plaintext)")

    # Nullable FK-like columns WITHOUT real FK constraint
    fk_like_count = rng.randint(1, 4)
    for i in range(fk_like_count):
        ref_col = f"parent_{rng.choice(_BUSINESS_NOUNS)}_id"
        columns.append(f"    {ref_col} INT NULL,  -- logical FK, not enforced")

    # Timestamps
    columns.append("    created_at DATETIME NULL,")
    columns.append("    updated_at DATETIME NULL")

    return (
        f"{comment}\n"
        f"CREATE TABLE {name} (\n"
        + "\n".join(columns)
        + "\n);\n"
    )


def _render_stored_proc(
    rng: random.Random,
    name: str,
    tables: list[str],
    last_modified_year: int,
) -> str:
    body_template = rng.choice(_STORED_PROC_STUBS)
    table = rng.choice(tables)
    other = rng.choice(tables)
    body = body_template.format(table=table, other=other)
    return (
        f"-- Last modified: {last_modified_year}-{rng.randint(1,12):02d}-"
        f"{rng.randint(1,28):02d}\n"
        f"CREATE PROCEDURE {name}\n"
        "    @period_id INT,\n"
        "    @since DATETIME\n"
        "AS\n"
        "BEGIN\n"
        "    SET NOCOUNT ON;\n"
        f"{body}\n"
        "END;\n"
    )


def generate_legacy_schema(
    app: AppRecipe,
    rng: random.Random,
    out_dir: Path,
) -> list[Path]:
    """Generate a schema.sql fixture for one app and return the created paths.

    Produces a single ``db/schema.sql`` file with:
      - Header comment describing the legacy profile
      - N tables (from the app's primary database spec, default 51)
      - Zero foreign key constraints (deliberately)
      - Stored procedures with stale "last modified" comments
      - PII columns stored in plaintext in ~half the tables
    """
    db_dir = out_dir / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    out_path = db_dir / "schema.sql"

    if not app.databases:
        # No DB spec — emit a minimal stub so the analyzer still sees something.
        out_path.write_text(
            "-- No database spec on this app. Placeholder only.\n",
            encoding="utf-8",
        )
        return [out_path]

    primary = app.databases[0]
    table_count = max(10, primary.tables)
    pii_tables = max(1, primary.pii_columns)
    engine = primary.engine

    used_names: set[str] = set()
    tables: list[str] = []
    table_renders: list[str] = []
    for i in range(table_count):
        name = _make_table_name(rng, used_names)
        tables.append(name)
        comment = rng.choice(_LEGACY_COMMENTS)
        has_pii = i < pii_tables
        table_renders.append(_render_table(rng, name, has_pii, comment))

    # Stored procedures — roughly the same legacy-app shape the Batch 3
    # findings described (~70, mostly unchanged since 2012)
    proc_count = rng.randint(max(20, table_count // 2), max(30, table_count))
    proc_renders: list[str] = []
    for i in range(proc_count):
        proc_name = f"sp_legacy_{i:03d}"
        year = 2012 if rng.random() < 0.85 else rng.randint(2013, 2018)
        proc_renders.append(_render_stored_proc(rng, proc_name, tables, year))

    header = (
        f"-- ---------------------------------------------------------------\n"
        f"-- Legacy schema fixture for {app.codename} ({app.label})\n"
        f"-- Engine: {engine}\n"
        f"-- Tables: {len(tables)}  Stored procedures: {len(proc_renders)}\n"
        f"-- Foreign keys: 0 (application enforces referential integrity)\n"
        f"-- Generator: NexusForge synth (deterministic, seeded)\n"
        f"-- ---------------------------------------------------------------\n\n"
    )

    content = header + "\n".join(table_renders) + "\n\n" + "\n".join(proc_renders)
    out_path.write_text(content, encoding="utf-8")
    return [out_path]
