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

from .languages import CSharpGenerator, CobolGenerator, PythonGenerator
from .profile import AppRecipe, TenantProfile, load_profile


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
    return replace(app, modules=new_modules)


def _generate_app(
    app: AppRecipe, tenant_seed: int, out_dir: Path, scale: float = 1.0
) -> int:
    """Generate one app and return the file count written."""
    scaled = _scale_app(app, scale)
    seed = _derive_seed(tenant_seed, scaled.codename)
    rng = random.Random(seed)

    files_written = 0

    if scaled.primary_language == "csharp":
        gen = CSharpGenerator(app=scaled, rng=rng)
        files_written += len(gen.generate(out_dir))
    elif scaled.primary_language == "python":
        gen = PythonGenerator(app=scaled, rng=rng)
        files_written += len(gen.generate(out_dir))
    else:
        logger.warning(
            "Unsupported primary_language '%s' for %s — skipping",
            scaled.primary_language,
            scaled.codename,
        )

    # Additional Cobol layer if requested (app-05)
    if scaled.has_cobol_layer:
        cobol_gen = CobolGenerator(app=scaled, rng=rng)
        files_written += len(cobol_gen.generate(out_dir))

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
