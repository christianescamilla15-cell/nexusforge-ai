"""Tests for MythosScanner profile-aware calibration (P-009/P-010/P-011)."""
from __future__ import annotations

from app.security.mythos import Finding, MythosScanner
from app.synth.profile import EdgeSecurity, ExposureProfile, SecretManagement


# ── No profile: no-op ────────────────────────────────────────────────


def test_no_profile_no_calibration(tmp_path):
    scanner = MythosScanner(str(tmp_path))
    f = Finding(severity="critical", category="injection", title="SQLi", description="sqli detected")
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    assert scanner.findings == [f]
    assert f.severity == "critical"
    assert scanner.calibration_stats["profile_downgraded"] == 0


# ── Rule 1 — Vault-injected credentials are NOT hardcoded ────────────


def test_vault_injection_filters_env_var_secrets(tmp_path):
    sm = SecretManagement(
        product="hashicorp-vault",
        hash_based_injection=True,
        internal_alias="Bolt",
    )
    scanner = MythosScanner(str(tmp_path), secret_management=sm)
    f = Finding(
        severity="high", category="secrets",
        title="Credential read from env var",
        description="API key loaded from os.environ['DB_PASSWORD']",
    )
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    assert scanner.findings == []  # filtered as false positive
    assert scanner.calibration_stats["profile_filtered"] == 1


def test_vault_injection_keeps_cwe_798_hardcoded(tmp_path):
    """CWE-798 = hardcoded credentials — should NOT be filtered even with Vault."""
    sm = SecretManagement(
        product="hashicorp-vault",
        hash_based_injection=True,
    )
    scanner = MythosScanner(str(tmp_path), secret_management=sm)
    f = Finding(
        severity="critical", category="secrets",
        title="Hardcoded password",
        description="os.environ read but also literal 'password123' in source",
        cwe="CWE-798",
    )
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    assert f in scanner.findings  # kept
    assert f.severity == "critical"


def test_vault_injection_keeps_non_env_var_secrets(tmp_path):
    sm = SecretManagement(product="hashicorp-vault", hash_based_injection=True)
    scanner = MythosScanner(str(tmp_path), secret_management=sm)
    f = Finding(
        severity="high", category="secrets",
        title="Hardcoded token",
        description="Literal API token in source file",
    )
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    assert f in scanner.findings  # not env var → not filtered


# ── Rule 2 — WAF mitigation for SQLi/XSS ─────────────────────────────


def test_waf_downgrades_sqli_injection(tmp_path):
    es = EdgeSecurity(
        waf_present=True,
        waf_provider="corporate",
        pattern_rules=["sqli", "xss", "rate-limit"],
    )
    scanner = MythosScanner(str(tmp_path), edge_security=es)
    f = Finding(
        severity="critical", category="injection",
        title="SQL Injection via concatenation",
        description="sqli vector found",
    )
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    assert f.severity == "high"  # downgraded
    assert "[WAF-mitigated]" in f.description
    assert scanner.calibration_stats["profile_downgraded"] == 1


def test_waf_downgrades_xss(tmp_path):
    es = EdgeSecurity(waf_present=True, pattern_rules=["sqli", "xss"])
    scanner = MythosScanner(str(tmp_path), edge_security=es)
    f = Finding(
        severity="high", category="injection",
        title="Cross-site scripting",
        description="xss found",
    )
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    assert f.severity == "medium"


def test_waf_does_not_affect_non_injection_category(tmp_path):
    es = EdgeSecurity(waf_present=True, pattern_rules=["sqli", "xss"])
    scanner = MythosScanner(str(tmp_path), edge_security=es)
    f = Finding(
        severity="critical", category="auth",
        title="JWT hardcoded",
        description="secret in code",
    )
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    assert f.severity == "critical"


def test_waf_without_sqli_xss_rules_does_nothing(tmp_path):
    es = EdgeSecurity(waf_present=True, pattern_rules=["rate-limit"])  # no sqli/xss
    scanner = MythosScanner(str(tmp_path), edge_security=es)
    f = Finding(severity="critical", category="injection", title="SQL injection", description="")
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    assert f.severity == "critical"


# ── Rule 3 — internal-only tag ───────────────────────────────────────


def test_internal_only_tags_findings(tmp_path):
    exp = ExposureProfile(surface="internal-only")
    scanner = MythosScanner(str(tmp_path), exposure=exp)
    f = Finding(
        severity="high", category="injection",
        title="SQL injection", description="internal endpoint",
    )
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    assert "[internal-only]" in f.description
    assert scanner.calibration_stats["profile_tagged"] == 1


def test_internal_only_does_not_tag_secrets(tmp_path):
    exp = ExposureProfile(surface="internal-only")
    scanner = MythosScanner(str(tmp_path), exposure=exp)
    f = Finding(
        severity="high", category="secrets",
        title="Hardcoded credential", description="creds here",
    )
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    assert "[internal-only]" not in f.description


def test_public_internet_does_not_tag(tmp_path):
    exp = ExposureProfile(surface="public-internet")
    scanner = MythosScanner(str(tmp_path), exposure=exp)
    f = Finding(severity="high", category="injection", title="SQLi", description="orig")
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    assert "[internal-only]" not in f.description


# ── Combined rules + idempotency ──────────────────────────────────────


def test_all_three_profiles_together(tmp_path):
    """WAF + Vault + internal-only applied in combination without collision."""
    es = EdgeSecurity(waf_present=True, pattern_rules=["sqli", "xss"])
    sm = SecretManagement(product="hashicorp-vault", hash_based_injection=True)
    exp = ExposureProfile(surface="internal-only")

    scanner = MythosScanner(
        str(tmp_path),
        edge_security=es,
        secret_management=sm,
        exposure=exp,
    )

    env_cred = Finding(
        severity="high", category="secrets",
        title="Env var credential",
        description="os.environ read",
    )
    sqli = Finding(
        severity="critical", category="injection",
        title="SQL injection",
        description="sqli in handler",
    )
    scanner.findings = [env_cred, sqli]
    scanner._apply_profile_calibration()

    # env_cred filtered by Vault rule
    assert env_cred not in scanner.findings
    # sqli downgraded by WAF + tagged internal-only
    assert sqli.severity == "high"
    assert "[WAF-mitigated]" in sqli.description
    assert "[internal-only]" in sqli.description


def test_profile_calibration_is_idempotent(tmp_path):
    es = EdgeSecurity(waf_present=True, pattern_rules=["sqli"])
    exp = ExposureProfile(surface="internal-only")
    scanner = MythosScanner(str(tmp_path), edge_security=es, exposure=exp)
    f = Finding(severity="critical", category="injection", title="SQLi", description="orig")
    scanner.findings = [f]
    scanner._apply_profile_calibration()
    first = f.description
    first_sev = f.severity
    scanner._apply_profile_calibration()
    assert f.description == first
    assert f.severity == first_sev  # downgrade happens once (high), not twice (medium)
