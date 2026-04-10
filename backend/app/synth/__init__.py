"""Synthetic codebase generator for NexusForge tenant showcases.

Produces deterministic, seeded, realistic legacy code that matches real
enterprise modernization profiles (multi-language, multi-database,
CWE-matching vulnerability density). The output is intended to be
ingested by NexusForge's refactor engine and demonstrate end-to-end
remediation at scale.

Entry point: `generator.generate_tenant(tenant_id)` reads a fixture
recipe file and writes a full directory tree under `synth_output/`.

Phase A targets 5 apps (~900K LOC). Phase B scales to 31 apps (~5.6M LOC).

All tenant names, app names and code identifiers are generic codenames.
No real client data ever appears here.
"""
from .profile import TenantProfile, AppRecipe, VulnerabilityDensity

__all__ = ["TenantProfile", "AppRecipe", "VulnerabilityDensity"]
