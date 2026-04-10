"""Showcase persistence layer (Batch 3 deliverable F5).

Stores snapshots of the showcase pipeline in PostgreSQL so the
client-facing /showcase endpoints can serve live data instead of the
static JSON fixtures under ``backend/showcase_data/``.

Usage:
    from app.showcase import storage

    # Write a new run
    run_id = await storage.save_run(
        tenant_slug="tenant-alpha",
        report=report_dict,
        compliance=compliance_dict,
        strangler_plans={"app-01": plan_dict, ...},
        duration_ms=720,
        source="pipeline",
    )

    # Read the most recent run for a tenant
    run = await storage.latest_run("tenant-alpha")
    if run:
        report = run["report"]
        compliance = run["compliance"]
        plans = run["strangler_plans"]

Endpoints in app/routes/refactor.py call ``latest_run`` first and fall
back to static JSON files when the query returns None, so the switch
is transparent to the frontend.
"""
from . import storage

__all__ = ["storage"]
