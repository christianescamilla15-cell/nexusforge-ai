"""Tests for Mythos baseline calibration (P-013).

Covers:
- Baseline YAML loading + schema
- Match by CWE
- Match by pattern keyword in title/description
- Effective-severity downgrade when mitigation is present
- Quick-win annotation
- Filtering policy (in-remediation + medium/low only)
- Integration with MythosScanner post-scan calibration
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.security.baseline_calibration import (
    BaselineCalibration,
    BaselineEntry,
    CalibrationMatch,
    _YAML_AVAILABLE,
)
from app.security.mythos import Finding, MythosScanner


# ── Fixture paths ──────────────────────────────────────────────────────

BASELINE_YAML = Path(__file__).parent.parent / "app" / "security" / "baselines" / "tenant-alpha-vulns-baseline.yaml"


# ── Baseline loading ──────────────────────────────────────────────────


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_baseline_loads_from_default_path():
    b = BaselineCalibration()
    assert b.is_loaded() is True
    assert len(b.entries) >= 15  # at least 9 ARC + 6 BSP
    assert b.version == "1.0.0"


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_baseline_has_expected_mitigations():
    b = BaselineCalibration(BASELINE_YAML)
    assert "waf" in b.mitigations
    assert "vault" in b.mitigations
    assert "encrypted_config" in b.mitigations
    assert b.mitigations["vault"].internal_alias == "Bolt"
    assert b.mitigations["vault"].on_premise is True


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_baseline_critical_entries_count():
    b = BaselineCalibration(BASELINE_YAML)
    # 9 ARC baseline (7 explicit, 2 placeholder not in this iteration) + some from BSP/app-01/app-02/app-05
    criticals = b.critical_entries()
    assert len(criticals) >= 10
    # Verify ARC has 7 explicitly modelled criticals
    arc_criticals = [e for e in criticals if e.app == "app-03-arc"]
    assert len(arc_criticals) >= 7


# ── Query/match API ────────────────────────────────────────────────────


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_entries_for_app_filters_correctly():
    b = BaselineCalibration(BASELINE_YAML)
    arc = b.entries_for_app("app-03-arc")
    assert len(arc) >= 7
    assert all(e.app == "app-03-arc" for e in arc)


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_match_by_cwe_arc_jwt():
    b = BaselineCalibration(BASELINE_YAML)
    # CWE-798 + at least one of the entry's pattern_match keywords
    # ("jwt-hardcoded", "jwt-secret-fallback", "hardcoded-secret") in
    # the haystack — required after the F-01 hijack guard was added.
    m = b.match(
        category="auth",
        app="app-03-arc",
        title="Hardcoded secret detected",
        description="jwt-hardcoded fallback in auth code",
        cwe="CWE-798",
    )
    assert m.matched is True
    assert m.entry is not None
    assert m.entry.id == "arc-jwt-hardcoded"


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_cwe_only_match_does_not_hijack_when_no_pattern_present():
    """F-01 regression: a finding whose CWE matches a baseline entry but
    whose haystack contains none of that entry's pattern_match keywords
    must NOT be filtered. Without the guard, a real CWE-798 finding in
    routes/auth.py would silently match a baseline entry intended for
    synth/vulnerabilities/*.cs and disappear into the by-design bucket.
    """
    b = BaselineCalibration(BASELINE_YAML)
    # arc-jwt-hardcoded has CWE-798 + patterns
    # ["jwt-hardcoded", "jwt-secret-fallback", "hardcoded-secret"].
    # This finding has the same CWE but a description that mentions
    # none of those literal tokens.
    m = b.match(
        category="auth",
        app="app-03-arc",
        title="Generic secret in code",
        description="API key found in module body",
        cwe="CWE-798",
        file_path="src/api/keys.py",
    )
    assert m.matched is False, (
        "CWE alone must not hijack: pattern must also appear in the haystack."
    )


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_cwe_match_honored_when_pattern_match_is_empty():
    """The guard exempts entries with empty pattern_match (broad CWE
    rules). Synthesized inline because no current baseline entry has
    both CWE set and pattern_match empty."""
    b = BaselineCalibration(BASELINE_YAML)
    broad = BaselineEntry(
        id="broad-cwe-rule", app="app-03-arc", category="auth",
        cwe="CWE-9999", pattern_match=[], severity="medium",
    )
    b.entries.append(broad)
    try:
        m = b.match(
            category="auth", app="app-03-arc",
            title="anything", description="anything", cwe="CWE-9999",
        )
        assert m.matched is True
        assert m.entry is broad
    finally:
        b.entries.remove(broad)


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_match_by_pattern_keyword_cors_wildcard():
    b = BaselineCalibration(BASELINE_YAML)
    m = b.match(
        category="config",
        app="app-03-arc",
        title="CORS misconfiguration",
        description="cors-wildcard origin allows any site",
    )
    assert m.matched is True
    assert m.entry.id == "arc-cors-wildcard"


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_match_xss_downgrades_severity_due_to_waf():
    b = BaselineCalibration(BASELINE_YAML)
    m = b.match(
        category="injection",
        app="app-03-arc",
        title="Cross-Site Scripting",
        description="reflected-xss in query param",
    )
    assert m.matched is True
    assert m.effective_severity == "high"  # downgraded from critical
    assert "mitigation" in m.downgrade_reason
    assert m.entry.severity == "critical"


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_match_flask_debug_flags_quick_win():
    b = BaselineCalibration(BASELINE_YAML)
    m = b.match(
        category="config",
        app="app-03-bsp",
        title="Debug mode enabled in production",
        description="flask-debug-true with host 0.0.0.0",
    )
    assert m.matched is True
    assert m.quick_win is True
    assert m.entry.priority.upper().startswith("URGENT")


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_match_returns_no_match_when_no_app_specified_and_no_keyword():
    b = BaselineCalibration(BASELINE_YAML)
    m = b.match(
        category="auth",
        title="Random unrelated finding",
        description="nothing matches here",
    )
    assert m.matched is False


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_should_filter_policy():
    b = BaselineCalibration(BASELINE_YAML)
    # Critical finding in remediation → NOT filtered (team tracks progress)
    arc_sqli = next(e for e in b.entries if e.id == "arc-sqli-concat")
    match = CalibrationMatch(
        matched=True,
        entry=arc_sqli,
        effective_severity=arc_sqli.final_severity(),
        in_remediation=True,
    )
    # arc-sqli has effective_severity="high", so sev_rank=1 <2 → not filtered
    assert b.should_filter(match) is False

    # Manually synthesize a medium in-remediation → filtered
    fake_entry = BaselineEntry(
        id="fake", app="app-01", category="config",
        severity="medium", effective_severity="medium",
        remediation_status="in-progress",
    )
    fake_match = CalibrationMatch(
        matched=True, entry=fake_entry,
        effective_severity="medium", in_remediation=True,
    )
    assert b.should_filter(fake_match) is True


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_summary_includes_key_stats():
    b = BaselineCalibration(BASELINE_YAML)
    s = b.summary()
    assert s["version"] == "1.0.0"
    assert s["loaded"] is True
    assert "waf" in s["mitigations"]
    assert "vault" in s["mitigations"]
    assert s["entries"] >= 15
    assert "app-03-arc" in s["apps_covered"]
    assert s["ecosystem_context"]["total_issues"] == 189_997
    assert s["risk_exposure_usd"]["total"] == 18_500_000


# ── Scanner integration ───────────────────────────────────────────────


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_scanner_without_baseline_no_change(tmp_path):
    """Scanner without baseline attached leaves findings untouched."""
    scanner = MythosScanner(str(tmp_path))
    f = Finding(
        severity="critical", category="auth",
        title="JWT hardcoded",
        description="secret in code",
        cwe="CWE-798",
    )
    scanner.findings = [f]
    scanner._apply_baseline_calibration()
    assert scanner.findings == [f]
    assert f.severity == "critical"
    assert "calibrated" not in f.description


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_scanner_with_baseline_downgrades_and_annotates(tmp_path):
    """Scanner with baseline attached downgrades XSS severity (WAF mitigation)."""
    baseline = BaselineCalibration(BASELINE_YAML)
    scanner = MythosScanner(
        str(tmp_path),
        tenant_app="app-03-arc",
        baseline=baseline,
    )

    xss = Finding(
        severity="critical", category="injection",
        title="Reflected XSS",
        description="reflected-xss found in handler",
    )
    jwt = Finding(
        severity="critical", category="auth",
        title="Hardcoded JWT secret",
        description="jwt-hardcoded fallback in auth.py",
        cwe="CWE-798",
    )
    scanner.findings = [xss, jwt]
    scanner._apply_baseline_calibration()

    # XSS downgraded to high via WAF mitigation
    assert xss.severity == "high"
    assert "calibrated" in xss.description

    # JWT stays critical (no effective_severity override)
    assert jwt.severity == "critical"

    # Both matched
    assert scanner.calibration_stats["matched"] == 2
    assert scanner.calibration_stats["downgraded"] == 1


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_scanner_baseline_flags_quick_win(tmp_path):
    baseline = BaselineCalibration(BASELINE_YAML)
    scanner = MythosScanner(
        str(tmp_path),
        tenant_app="app-03-bsp",
        baseline=baseline,
    )
    flask_rce = Finding(
        severity="critical", category="config",
        title="Debug mode enabled",
        description="flask-debug-true host 0.0.0.0 in production",
        cwe="CWE-16",
    )
    scanner.findings = [flask_rce]
    scanner._apply_baseline_calibration()
    assert flask_rce.description.startswith("[QUICK WIN]")
    assert scanner.calibration_stats["quick_wins"] == 1


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_scanner_baseline_is_idempotent(tmp_path):
    """Re-running calibration does not double-annotate."""
    baseline = BaselineCalibration(BASELINE_YAML)
    scanner = MythosScanner(str(tmp_path), tenant_app="app-03-bsp", baseline=baseline)
    f = Finding(
        severity="critical", category="config",
        title="Flask debug on",
        description="flask-debug-true bind 0.0.0.0",
    )
    scanner.findings = [f]
    scanner._apply_baseline_calibration()
    first_desc = f.description
    scanner._apply_baseline_calibration()
    assert f.description == first_desc
