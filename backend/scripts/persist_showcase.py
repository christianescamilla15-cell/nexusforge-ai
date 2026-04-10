"""Persist a tenant's static showcase fixtures into the DB.

Reads the JSON files under ``backend/showcase_data/<tenant>/`` and
inserts a single ``showcase_runs`` row per invocation. Useful for
seeding the database in production without needing to re-run the
synth generator and the full pipeline.

After a successful persist, the ``/api/refactor/showcase/*`` endpoints
will return the DB row instead of the static fixture, so the frontend
can reflect live changes without a deploy.

USAGE:
    DATABASE_URL=postgres://... \\
      python backend/scripts/persist_showcase.py --tenant tenant-alpha

    # Dry-run — loads and validates the fixtures but does not write
    DATABASE_URL=postgres://... \\
      python backend/scripts/persist_showcase.py --tenant tenant-alpha --dry-run

    # Custom fixture directory
    DATABASE_URL=postgres://... \\
      python backend/scripts/persist_showcase.py \\
        --tenant tenant-alpha \\
        --data-dir /custom/path/to/showcase_data

EXIT CODES:
    0  Persisted (or dry-run succeeded)
    1  Runtime error (fixture missing, DB unreachable, corrupt JSON)
    2  Invalid arguments
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Allow running the script as ``python backend/scripts/persist_showcase.py``
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

DEFAULT_DATA_DIR = REPO_ROOT / "backend" / "showcase_data"


def _load_tenant_fixtures(
    data_dir: Path, tenant: str
) -> tuple[dict, dict | None, dict[str, dict]]:
    """Load and validate the three fixture categories for one tenant.

    Returns (report, compliance, strangler_plans). Raises FileNotFoundError
    if the required showcase_report.json is missing, or json.JSONDecodeError
    if any file is corrupt.
    """
    tenant_dir = data_dir / tenant
    report_path = tenant_dir / "showcase_report.json"
    if not report_path.exists():
        raise FileNotFoundError(
            f"No showcase_report.json at {report_path}. "
            f"Run the synth generator + showcase_run.py first."
        )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    compliance_path = tenant_dir / "compliance.json"
    compliance: dict | None = None
    if compliance_path.exists():
        compliance = json.loads(compliance_path.read_text(encoding="utf-8"))

    strangler_plans: dict[str, dict] = {}
    plans_dir = tenant_dir / "strangler_plans"
    if plans_dir.is_dir():
        for plan_file in sorted(plans_dir.glob("*.json")):
            app_codename = plan_file.stem
            strangler_plans[app_codename] = json.loads(
                plan_file.read_text(encoding="utf-8")
            )

    return report, compliance, strangler_plans


async def persist(
    tenant: str,
    data_dir: Path,
    dry_run: bool,
) -> None:
    """Main entry point — loads fixtures and writes the showcase_runs row."""
    report, compliance, strangler_plans = _load_tenant_fixtures(data_dir, tenant)

    # Print a preview regardless of dry-run
    totals = report.get("totals", {})
    print()
    print("=" * 60)
    print(f"Tenant:          {tenant}")
    print(f"Source dir:      {data_dir / tenant}")
    print(f"Apps:            {totals.get('apps', 0)}")
    print(f"Files:           {totals.get('files', 0):,}")
    print(f"LOC:             {totals.get('lines_of_code', 0):,}")
    print(f"Findings:        {totals.get('findings', 0):,}")
    print(f"Compliance:      {'yes' if compliance else 'no'}")
    print(f"Strangler plans: {len(strangler_plans)}")
    print("=" * 60)

    if dry_run:
        print("\nDRY-RUN: no database write.")
        return

    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL environment variable is not set")

    # Set a fake JWT_SECRET so app.config does not raise on import
    os.environ.setdefault(
        "JWT_SECRET",
        "persist-showcase-script-dummy-secret-must-be-32-bytes",
    )

    from app.showcase import storage

    run_id = await storage.save_run(
        tenant_slug=tenant,
        report=report,
        compliance=compliance,
        strangler_plans=strangler_plans,
        duration_ms=int(report.get("duration_ms", 0)),
        source="seed",
    )
    print(f"\nPersisted showcase run: id={run_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tenant",
        default="tenant-alpha",
        help="Tenant slug (matches the directory under showcase_data/)",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="Root directory containing showcase fixtures",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and validate the fixtures without writing to the DB",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    try:
        asyncio.run(persist(args.tenant, data_dir, args.dry_run))
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: corrupt JSON fixture: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
