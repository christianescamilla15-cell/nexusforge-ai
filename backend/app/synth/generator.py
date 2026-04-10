"""Top-level entry point for the synthetic tenant generator.

Given a tenant profile YAML, generates a full directory tree for the
tenant under ``synth_output/<tenant_id>/``. Each app gets its own
subdirectory with language-appropriate source files and vulnerability
density matching the recipe.

Usage:
    python -m app.synth.generator                  # all apps in default fixture
    python -m app.synth.generator --app app-01     # single app
    python -m app.synth.generator --fixture PATH   # custom fixture
    python -m app.synth.generator --output DIR     # custom output dir
"""
from __future__ import annotations

import argparse
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from .databases import generate_legacy_schema
from .languages import CSharpGenerator, CobolGenerator, PythonGenerator
from .profile import AppRecipe, SubProject, TenantProfile, VulnerabilityDensity, load_profile


logger = logging.getLogger(__name__)


DEFAULT_FIXTURE = Path(__file__).parent / "fixtures" / "tenant_alpha.yaml"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[3] / "synth_output"


@dataclass
class GenerationReport:
    tenant_id: str
    apps_generated: list[str] = field(default_factory=list)
    total_files: int = 0
    total_loc: int = 0
    total_vulnerabilities: int = 0
    duration_seconds: float = 0.0
    output_path: Path | None = None


def _derive_seed(tenant_seed: int, codename: str) -> int:
    # Deterministic per-app seed derived from tenant seed + codename hash.
    return tenant_seed ^ (abs(hash(codename)) & 0xFFFFFFFF)


def _scale_app(app: AppRecipe, scale: float) -> AppRecipe:
    """Return a copy of the app recipe with modules count multiplied by scale.

    Vulnerability budget is left unchanged so it distributes across the
    larger module set, which lowers per-module vulnerability density —
    the realistic outcome when a real codebase grows: more benign code,
    same absolute number of known vulns.
    """
    if scale == 1.0:
        return app
    from dataclasses import replace

    new_modules = max(1, int(round(app.modules * scale)))
    scaled_subs = [
        replace(sub, modules=max(1, int(round(sub.modules * scale))))
        for sub in app.sub_projects
    ]
    return replace(app, modules=new_modules, sub_projects=scaled_subs)


def _carve_sub_recipe(
    parent: AppRecipe, sub: SubProject, scale: float
) -> AppRecipe:
    """Derive a single-project AppRecipe for one sub-project.

    Splits the parent's vulnerability budget by ``sub.vuln_share`` and its
    LOC target by ``sub.loc_share``. The returned recipe has no
    ``sub_projects`` of its own so the existing single-project generator
    paths can consume it unchanged.
    """
    from dataclasses import replace

    vulns = parent.vulnerabilities
    share_vulns = VulnerabilityDensity(
        sql_injection=int(round(vulns.sql_injection * sub.vuln_share)),
        hardcoded_creds=int(round(vulns.hardcoded_creds * sub.vuln_share)),
        weak_crypto=int(round(vulns.weak_crypto * sub.vuln_share)),
        command_injection=int(round(vulns.command_injection * sub.vuln_share)),
        missing_fk=int(round(vulns.missing_fk * sub.vuln_share)),
        pii_leak=int(round(vulns.pii_leak * sub.vuln_share)),
        suppressed_exceptions=int(round(vulns.suppressed_exceptions * sub.vuln_share)),
    )
    scaled_modules = max(1, int(round(sub.modules * scale)))
    return replace(
        parent,
        codename=f"{parent.codename}-{sub.name}",
        label=f"{parent.label} — {sub.name}",
        loc_target=int(round(parent.loc_target * sub.loc_share)),
        primary_language=sub.language,
        additional_languages=[],
        modules=scaled_modules,
        sub_projects=[],
        has_rpa=sub.has_rpa,
        # The parent's has_cobol_layer flag is only meaningful for the
        # legacy Cobol injection path; sub-project paths always bypass it
        # since the Cobol sub-project is explicit in the recipe already.
        has_cobol_layer=False,
        # DB schema injection lives at the parent level; do not re-emit
        # from every sub-project.
        inject_legacy_db_schema=False,
        decision=None,
    )


def _dispatch_language(
    app: AppRecipe, rng: random.Random, out_dir: Path
) -> int:
    """Call the right language generator for a single-project app."""
    lang = app.primary_language
    if lang == "csharp":
        return len(CSharpGenerator(app=app, rng=rng).generate(out_dir))
    if lang == "python":
        return len(PythonGenerator(app=app, rng=rng).generate(out_dir))
    if lang == "cobol":
        return len(CobolGenerator(app=app, rng=rng).generate(out_dir))
    logger.warning(
        "Unsupported language '%s' for %s — writing placeholder README",
        lang,
        app.codename,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    placeholder = out_dir / "README.md"
    placeholder.write_text(
        f"# {app.label}\n\n"
        f"Placeholder for `{lang}` sub-project. Language generator not "
        f"yet implemented — contributions welcome.\n",
        encoding="utf-8",
    )
    return 1


def _generate_app(
    app: AppRecipe, tenant_seed: int, out_dir: Path, scale: float = 1.0
) -> int:
    """Generate one app and return the file count written.

    If the recipe has ``sub_projects``, each sub-project is written to its
    own subdirectory using its language and its share of the parent's
    vulnerability / LOC budget. Otherwise the single-project path is
    used (unchanged from pre-Batch-3 behaviour).
    """
    scaled = _scale_app(app, scale)
    seed = _derive_seed(tenant_seed, scaled.codename)

    files_written = 0

    if scaled.sub_projects:
        for sub in scaled.sub_projects:
            sub_out = out_dir / sub.name
            sub_recipe = _carve_sub_recipe(scaled, sub, scale)
            sub_rng = random.Random(_derive_seed(seed, sub.name))
            files_written += _dispatch_language(sub_recipe, sub_rng, sub_out)
    else:
        rng = random.Random(seed)
        if scaled.primary_language == "csharp":
            files_written += len(CSharpGenerator(app=scaled, rng=rng).generate(out_dir))
        elif scaled.primary_language == "python":
            files_written += len(PythonGenerator(app=scaled, rng=rng).generate(out_dir))
        else:
            logger.warning(
                "Unsupported primary_language '%s' for %s — skipping",
                scaled.primary_language,
                scaled.codename,
            )

        # Additional Cobol layer if requested (single-project apps only).
        # Multi-sub-project apps should list cobol explicitly as a sub-project.
        if scaled.has_cobol_layer and not scaled.sub_projects:
            cobol_rng = random.Random(_derive_seed(seed, "cobol"))
            files_written += len(
                CobolGenerator(app=scaled, rng=cobol_rng).generate(out_dir)
            )

    # Legacy DB schema fixture (Batch 3) — single schema per app at the app root
    if scaled.inject_legacy_db_schema:
        db_rng = random.Random(_derive_seed(seed, "db-schema"))
        files_written += len(generate_legacy_schema(scaled, db_rng, out_dir))

    # Refactor decision markdown (Batch 3) — one per app with an assigned decision
    if scaled.decision is not None:
        decision_path = out_dir / "refactor_decision.md"
        decision_path.parent.mkdir(parents=True, exist_ok=True)
        decision_path.write_text(
            scaled.decision.to_markdown(scaled.codename, scaled.label),
            encoding="utf-8",
        )
        files_written += 1

    # db_inactive_since marker (Batch 3) — signals retirement-path heuristics
    # to the strangler planner without requiring a full decision block.
    if scaled.db_inactive_since:
        marker_path = out_dir / "db_inactive_since.txt"
        marker_path.write_text(
            f"{scaled.db_inactive_since}\n"
            f"# This file is emitted by the synth generator when a recipe sets\n"
            f"# db_inactive_since. The strangler planner reads it as a signal\n"
            f"# that the underlying database has been inactive for long enough\n"
            f"# to consider retirement, pending dual validation.\n",
            encoding="utf-8",
        )
        files_written += 1

    return files_written


def _count_loc(dir_path: Path) -> int:
    total = 0
    for p in dir_path.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".cs", ".py", ".cob", ".jcl", ".config", ".md"}:
            continue
        try:
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                total += sum(1 for _ in f)
        except OSError:
            continue
    return total


def generate_tenant(
    profile: TenantProfile,
    output_dir: Path,
    only_app: str | None = None,
    scale: float = 1.0,
) -> GenerationReport:
    """Generate the full tenant tree. Returns a report with metrics.

    ``scale`` multiplies each app's module count. Use scale>1 to hit
    larger LOC targets (e.g., scale=10 turns a 12-module recipe into
    120 modules, producing roughly 10x the LOC with the same absolute
    vulnerability budget spread across more files).
    """
    start = time.monotonic()
    report = GenerationReport(tenant_id=profile.tenant_id)

    tenant_out = output_dir / profile.tenant_id
    tenant_out.mkdir(parents=True, exist_ok=True)

    for app in profile.apps:
        if only_app and app.codename != only_app:
            continue

        app_out = tenant_out / app.codename
        logger.info("Generating %s (%s) at %s", app.codename, app.label, app_out)

        files = _generate_app(app, profile.seed, app_out, scale=scale)

        # Write a synthetic README.md per app so ingestion picks up metadata
        (app_out / "README.md").write_text(
            f"# {app.label}\n\n"
            f"Codename: `{app.codename}`\n"
            f"Primary language: {app.primary_language}\n"
            f"Modules: {app.modules}\n"
            f"LOC target: {app.loc_target:,}\n"
            f"Databases: {', '.join(d.engine for d in app.databases) or 'n/a'}\n\n"
            f"_Synthetic code generated by NexusForge synth module. Not real client data._\n",
            encoding="utf-8",
        )
        files += 1

        report.apps_generated.append(app.codename)
        report.total_files += files
        report.total_vulnerabilities += app.vulnerabilities.total()

    report.output_path = tenant_out
    report.total_loc = _count_loc(tenant_out)
    report.duration_seconds = round(time.monotonic() - start, 2)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="Path to tenant YAML")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output root directory")
    parser.add_argument("--app", default=None, help="Generate only this app codename")
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help=(
            "Module-count multiplier for LOC scaling. 1.0 = recipe defaults "
            "(~21K LOC tenant). 10 = ~200K LOC. ~43 = phase A target ~900K LOC. "
            "~260 = phase B target ~5.6M LOC."
        ),
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress INFO logs")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    profile = load_profile(args.fixture)
    output_dir = Path(args.output).resolve()

    print(
        f"\nGenerating synthetic tenant '{profile.tenant_id}' "
        f"({profile.display_name}) -> {output_dir}"
    )
    print(
        f"Profile: {len(profile.apps)} apps, ~{profile.total_loc():,} LOC target, "
        f"{profile.total_vulnerabilities():,} vulnerabilities"
    )
    if args.scale != 1.0:
        print(f"Scale: {args.scale}x (module counts multiplied)")
    if args.app:
        print(f"Filter: only {args.app}")

    report = generate_tenant(profile, output_dir, only_app=args.app, scale=args.scale)

    print("\n=== Generation Report ===")
    print(f"Tenant:              {report.tenant_id}")
    print(f"Apps generated:      {len(report.apps_generated)} ({', '.join(report.apps_generated)})")
    print(f"Files written:       {report.total_files}")
    print(f"LOC produced:        {report.total_loc:,}")
    print(f"Vulnerabilities:     {report.total_vulnerabilities:,} (configured in recipe)")
    print(f"Duration:            {report.duration_seconds}s")
    print(f"Output path:         {report.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
