"""Mythos baseline calibration — P-013.

Loads a tenant-specific baseline of known findings + mitigation layers and
exposes matching/calibration helpers that Mythos scanners can use to:

1. Match a scanner finding against a known baseline entry (by category +
   pattern keywords + optional CWE).
2. Apply effective-severity downgrades when a mitigation layer covers the
   finding (e.g., XSS with a WAF in front).
3. Flag quick wins (single-line fixes) so they surface at the top.
4. Annotate findings with remediation status from the discovery corpus.

The calibration is **read-only**: scanners query the baseline, the baseline
never mutates scanner state directly. Callers decide whether to:
  - Filter (drop) known findings
  - Downgrade severity
  - Attach metadata for reporting

Baseline format lives in
``app/security/baselines/tenant-alpha-vulns-baseline.yaml`` — see that file
for the structure contract.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _YAML_AVAILABLE = False


_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


@dataclass
class BaselineEntry:
    """One known finding from the external baseline."""

    id: str
    app: str
    category: str
    pattern_match: list[str] = field(default_factory=list)
    cwe: str = ""
    severity: str = "medium"
    effective_severity: str = ""       # optional downgrade (mitigation applied)
    remediation_status: str = ""
    remediation_phase: str = ""
    remediation_target: str = ""
    mitigation_layer: str = ""
    quick_win: str = ""
    priority: str = ""
    context: str = ""
    note: str = ""
    source: str = ""

    def final_severity(self) -> str:
        """Return the severity the scanner should surface after calibration."""
        return self.effective_severity or self.severity


@dataclass
class Mitigation:
    """A mitigation layer present in the environment."""

    name: str
    provider: str = ""
    applies_to: list[str] = field(default_factory=list)
    blocks_patterns: list[str] = field(default_factory=list)
    effect: str = ""
    internal_alias: str = ""
    on_premise: bool = False


@dataclass
class CalibrationMatch:
    """The outcome of matching a scanner finding against the baseline."""

    matched: bool
    entry: BaselineEntry | None = None
    effective_severity: str = ""
    quick_win: bool = False
    in_remediation: bool = False
    filtered: bool = False             # if True, caller should drop the finding
    downgrade_reason: str = ""


class BaselineCalibration:
    """Loads and queries a tenant-alpha vulnerability baseline."""

    def __init__(self, baseline_path: str | Path | None = None) -> None:
        self.entries: list[BaselineEntry] = []
        self.mitigations: dict[str, Mitigation] = {}
        self.ecosystem_context: dict[str, Any] = {}
        self.risk_exposure_usd: dict[str, Any] = {}
        self.version: str = "unknown"
        self._loaded: bool = False

        if baseline_path is None:
            baseline_path = Path(__file__).parent / "baselines" / "tenant-alpha-vulns-baseline.yaml"
        self.baseline_path = Path(baseline_path)

        if self.baseline_path.is_file():
            self._load()

    def _load(self) -> None:
        if not _YAML_AVAILABLE:
            logger.warning("PyYAML not installed — baseline calibration disabled")
            return
        try:
            text = self.baseline_path.read_text(encoding="utf-8")
            data = yaml.safe_load(text) or {}
        except Exception as exc:
            logger.warning("Failed to load baseline %s: %s", self.baseline_path, exc)
            return

        self.version = str(data.get("version", "unknown"))

        for name, mit in (data.get("mitigations") or {}).items():
            self.mitigations[name] = Mitigation(
                name=name,
                provider=mit.get("provider", ""),
                applies_to=list(mit.get("applies_to") or []),
                blocks_patterns=list(mit.get("blocks_patterns") or []),
                effect=mit.get("effect", ""),
                internal_alias=mit.get("internal_alias", ""),
                on_premise=bool(mit.get("on_premise", False)),
            )

        for row in (data.get("findings") or []):
            if not isinstance(row, dict) or "id" not in row:
                continue
            self.entries.append(BaselineEntry(
                id=row["id"],
                app=row.get("app", ""),
                category=row.get("category", ""),
                pattern_match=list(row.get("pattern_match") or []),
                cwe=row.get("cwe", ""),
                severity=row.get("severity", "medium"),
                effective_severity=row.get("effective_severity", ""),
                remediation_status=row.get("remediation_status", ""),
                remediation_phase=row.get("remediation_phase", ""),
                remediation_target=row.get("remediation_target", ""),
                mitigation_layer=row.get("mitigation_layer", ""),
                quick_win=row.get("quick_win", ""),
                priority=row.get("priority", ""),
                context=row.get("context", ""),
                note=row.get("note", ""),
                source=row.get("source", ""),
            ))

        self.ecosystem_context = dict(data.get("ecosystem_context") or {})
        self.risk_exposure_usd = dict(data.get("risk_exposure_usd") or {})
        self._loaded = True
        logger.info(
            "Baseline loaded: %d entries, %d mitigations (v%s)",
            len(self.entries), len(self.mitigations), self.version,
        )

    # ── Query API ────────────────────────────────────────────────────

    def is_loaded(self) -> bool:
        return self._loaded

    def entries_for_app(self, app: str) -> list[BaselineEntry]:
        return [e for e in self.entries if e.app == app]

    def critical_entries(self) -> list[BaselineEntry]:
        return [e for e in self.entries if e.severity == "critical"]

    def quick_wins(self) -> list[BaselineEntry]:
        return [e for e in self.entries if e.quick_win]

    def urgent_priorities(self) -> list[BaselineEntry]:
        return [e for e in self.entries if e.priority.upper().startswith("URGENT")]

    def match(
        self,
        *,
        category: str,
        app: str = "",
        title: str = "",
        description: str = "",
        cwe: str = "",
        file_path: str = "",
    ) -> CalibrationMatch:
        """Match a scanner finding against the baseline.

        Strategy (first hit wins):
          1. If CWE is provided and matches an entry for the same app →
             hit (only if pattern_match is empty OR one of its patterns
             also appears in the haystack — prevents CWE-only hijack).
          2. Else, match on category + app + any pattern keyword found
             in (title + description + file_path).

        Returns a ``CalibrationMatch`` describing the outcome and any
        downgrade/quick-win/remediation metadata.
        """
        if not self._loaded:
            return CalibrationMatch(matched=False)

        haystack = f"{title} {description} {file_path}".lower()

        # Narrow down by app (if provided) + category
        candidates = [e for e in self.entries if e.category == category]
        if app:
            candidates = [e for e in candidates if e.app == app or not e.app]

        # 1. CWE first — but only honor the match when the entry has no
        # pattern_match (broad rule) OR at least one of its patterns
        # also appears in the haystack. Without this guard a CWE-only
        # hit on, say, CWE-798 in routes/auth.py would silently match a
        # baseline entry intended for synth/vulnerabilities/*.cs and
        # filter the real finding as "by-design". Documented in the
        # docstring above; this is the implementation.
        if cwe:
            cwe_norm = cwe.upper().replace(" ", "")
            for e in candidates:
                if e.cwe and e.cwe.upper().replace(" ", "") == cwe_norm:
                    if not e.pattern_match or any(
                        p.lower() in haystack for p in e.pattern_match
                    ):
                        return self._build_match(e)

        # 2. Pattern keyword — matches against title + description +
        # file_path. Lets calibration filter by file location (e.g.,
        # synth/vulnerabilities/ intentional fixtures).
        for e in candidates:
            for pat in e.pattern_match:
                if pat.lower() in haystack:
                    return self._build_match(e)

        return CalibrationMatch(matched=False)

    def _build_match(self, entry: BaselineEntry) -> CalibrationMatch:
        effective = entry.final_severity()
        downgrade_reason = ""
        if entry.effective_severity and entry.effective_severity != entry.severity:
            downgrade_reason = f"mitigation={entry.mitigation_layer or 'context'}"
        return CalibrationMatch(
            matched=True,
            entry=entry,
            effective_severity=effective,
            quick_win=bool(entry.quick_win),
            in_remediation=bool(entry.remediation_status or entry.remediation_phase),
            filtered=False,
            downgrade_reason=downgrade_reason,
        )

    def should_filter(self, match: CalibrationMatch) -> bool:
        """Decide if a known finding should be filtered out entirely.

        Policy:
          1. ``remediation_status ∈ {"by-design", "accepted-risk", "false-positive"}``
             → ALWAYS filter, regardless of severity. These are known
             non-issues that shouldn't consume triage bandwidth.
          2. In-active-remediation + effective severity ≤ medium → filter.
             Critical in-remediation findings still surface so the team
             can track progress.
        """
        if not match.matched or not match.entry:
            return False

        status = (match.entry.remediation_status or "").lower()
        if status in ("by-design", "accepted-risk", "false-positive"):
            # F-05 (2026-04-25): when a CRITICAL or HIGH finding is
            # filtered out as accepted-risk / by-design, log a WARNING
            # so the entry remains visible in scan logs. Policy (filter
            # silently from the report) is unchanged — but a wrong
            # `accepted-risk` tag on a critical finding used to be
            # entirely invisible. Now it appears in CloudWatch / stdout
            # at WARN level for monthly review.
            if match.effective_severity in ("critical", "high"):
                logger.warning(
                    "Mythos baseline filtered %s/%s finding: id=%s app=%s status=%s",
                    match.effective_severity,
                    match.entry.severity,
                    match.entry.id,
                    match.entry.app or "(any)",
                    status,
                )
            return True

        sev_rank = _SEVERITY_ORDER.get(match.effective_severity, 2)
        return match.in_remediation and sev_rank >= 2  # medium/low

    # ── Reporting helpers ────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "baseline_path": str(self.baseline_path),
            "loaded": self._loaded,
            "entries": len(self.entries),
            "mitigations": list(self.mitigations.keys()),
            "apps_covered": sorted({e.app for e in self.entries if e.app}),
            "by_severity": self._count_by_severity(),
            "quick_wins": len(self.quick_wins()),
            "urgent": len(self.urgent_priorities()),
            "ecosystem_context": self.ecosystem_context,
            "risk_exposure_usd": self.risk_exposure_usd,
        }

    def _count_by_severity(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.entries:
            sev = e.final_severity()
            out[sev] = out.get(sev, 0) + 1
        return out
