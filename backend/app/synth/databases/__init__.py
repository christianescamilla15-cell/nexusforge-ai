"""Database schema fixture generators.

These emit realistic legacy SQL schemas that the NexusForge database
integrity analyzer can ingest. The standard legacy shape is defined in
``legacy_schema.py`` and matches the Batch 3 "typical enterprise
nexus DB" profile (51+ tables, 0 FK, 70+ stored procedures, most
unchanged since ~2012).
"""
from .legacy_schema import generate_legacy_schema

__all__ = ["generate_legacy_schema"]
