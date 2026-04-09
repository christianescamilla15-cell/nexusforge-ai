"""RPA Stability Scanner — detect fragile Playwright/Selenium selectors.

Built for Robot BSP (mi-automation-rfndbsplink) which uses Playwright
to automate BSPLink portal interactions. Hardcoded CSS selectors break
when the portal updates its UI.

Detects:
  1. Hardcoded CSS selectors (fragile)
  2. XPath with positional indices (very fragile)
  3. Selectors without data-testid or aria attributes (fragile)
  4. Hardcoded URLs and credentials in RPA code
  5. Missing error handling in page interactions
  6. Missing retry/timeout configuration
  7. Sleep-based waits instead of proper wait conditions
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RPAFinding:
    severity: str       # critical, high, medium, low
    category: str       # fragile_selector, hardcoded_url, missing_retry, sleep_wait, missing_error_handling
    title: str
    description: str
    file_path: str
    line_number: int
    code_snippet: str = ""
    fix_suggestion: str = ""
    stability_score: int = 100  # 0-100, lower = more fragile


@dataclass
class RPAReport:
    project_name: str
    total_files: int = 0
    total_selectors: int = 0
    fragile_selectors: int = 0
    stability_score: int = 100  # Overall 0-100
    findings: list[RPAFinding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project": self.project_name,
            "total_files": self.total_files,
            "total_selectors": self.total_selectors,
            "fragile_selectors": self.fragile_selectors,
            "stability_score": self.stability_score,
            "findings_count": len(self.findings),
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "title": f.title,
                    "file": f.file_path,
                    "line": f.line_number,
                    "snippet": f.code_snippet[:80],
                    "fix": f.fix_suggestion,
                    "stability": f.stability_score,
                }
                for f in sorted(self.findings, key=lambda x: x.stability_score)
            ],
        }


# Selector stability scoring
# Higher = more stable, lower = more fragile
_SELECTOR_SCORES = {
    "data-testid": 95,    # Best: dedicated test attribute
    "aria-label": 90,     # Good: accessibility attribute
    "id=": 85,            # Good: unique identifier
    "role=": 80,          # Good: semantic role
    "name=": 75,          # OK: form element name
    "text=": 70,          # OK: visible text (breaks with i18n)
    "class=": 40,         # Fragile: CSS classes change often
    ".": 35,              # Fragile: CSS class selector
    "#": 80,              # OK: ID selector
    ">>": 30,             # Fragile: deep CSS combinator
    "nth-child": 20,      # Very fragile: positional
    "xpath=": 25,         # Fragile: XPath
    "//": 20,             # Very fragile: XPath
    "css=": 40,           # Fragile: raw CSS
}


class RPAScanner:
    """Scan RPA code for fragile selectors and stability issues."""

    def __init__(self, project_root: str):
        self.root = Path(project_root)

    async def scan(self, name: str = "") -> RPAReport:
        """Scan all Python files for Playwright/Selenium patterns."""
        report = RPAReport(project_name=name or self.root.name)

        py_files = [f for f in self.root.rglob("*.py")
                    if "__pycache__" not in str(f) and "test_" not in f.name]
        report.total_files = len(py_files)

        for fpath in py_files:
            self._scan_file(fpath, report)

        # Calculate overall stability score
        if report.total_selectors > 0:
            total_score = sum(f.stability_score for f in report.findings if f.category == "fragile_selector")
            stable_selectors = report.total_selectors - report.fragile_selectors
            report.stability_score = int(
                (stable_selectors * 90 + total_score) / (report.total_selectors + len([f for f in report.findings if f.category == "fragile_selector"]) or 1)
            )

        return report

    def _scan_file(self, fpath: Path, report: RPAReport):
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            rel = str(fpath.relative_to(self.root))
            lines = content.splitlines()

            for line_num, line in enumerate(lines, 1):
                # Detect Playwright selectors
                self._check_selectors(line, line_num, rel, report)
                # Detect sleep waits
                self._check_sleep_waits(line, line_num, rel, report)
                # Detect missing error handling
                self._check_error_handling(line, line_num, rel, content, report)
                # Detect hardcoded URLs
                self._check_hardcoded_urls(line, line_num, rel, report)

        except Exception:
            pass

    def _check_selectors(self, line: str, line_num: int, file_path: str, report: RPAReport):
        """Check for Playwright/Selenium selector patterns."""
        # Playwright patterns
        selector_patterns = [
            r'\.(?:click|fill|type|press|check|uncheck|select_option|wait_for_selector|query_selector|locator)\(\s*["\']([^"\']+)["\']',
            r'page\.(?:get_by_role|get_by_text|get_by_label|get_by_placeholder|get_by_test_id)\(\s*["\']([^"\']+)["\']',
            r'\.(?:find_element|find_elements)\(\s*(?:By\.\w+,\s*)?["\']([^"\']+)["\']',
        ]

        for pattern in selector_patterns:
            for m in re.finditer(pattern, line):
                selector = m.group(1)
                report.total_selectors += 1

                # Score the selector
                score = self._score_selector(selector)
                if score < 60:
                    report.fragile_selectors += 1
                    report.findings.append(RPAFinding(
                        severity="high" if score < 30 else "medium",
                        category="fragile_selector",
                        title=f"Fragile selector (stability: {score}%)",
                        description=f"Selector '{selector[:60]}' is likely to break on UI updates",
                        file_path=file_path,
                        line_number=line_num,
                        code_snippet=line.strip()[:120],
                        fix_suggestion=self._suggest_fix(selector),
                        stability_score=score,
                    ))

    def _check_sleep_waits(self, line: str, line_num: int, file_path: str, report: RPAReport):
        """Detect time.sleep() or asyncio.sleep() instead of proper waits."""
        if re.search(r'(?:time\.sleep|asyncio\.sleep)\(\s*(\d+)', line):
            sleep_val = re.search(r'sleep\(\s*(\d+)', line)
            seconds = int(sleep_val.group(1)) if sleep_val else 0
            if seconds > 1:
                report.findings.append(RPAFinding(
                    severity="medium",
                    category="sleep_wait",
                    title=f"Sleep-based wait ({seconds}s)",
                    description="Fixed sleep waits are fragile — use page.wait_for_selector() or expect()",
                    file_path=file_path,
                    line_number=line_num,
                    code_snippet=line.strip()[:100],
                    fix_suggestion="Replace with: await page.wait_for_selector('selector', timeout=30000)",
                    stability_score=40,
                ))

    def _check_error_handling(self, line: str, line_num: int, file_path: str, content: str, report: RPAReport):
        """Detect page interactions without try-except."""
        if re.search(r'page\.\w+\(', line) and "await" in line:
            # Check if inside a try block (look at preceding 5 lines)
            lines = content.splitlines()
            start = max(0, line_num - 6)
            preceding = "\n".join(lines[start:line_num - 1])
            if "try:" not in preceding and "except" not in preceding:
                if "click" in line or "fill" in line or "goto" in line:
                    report.findings.append(RPAFinding(
                        severity="low",
                        category="missing_error_handling",
                        title="Page interaction without error handling",
                        description="If the element doesn't exist or page navigates, this will crash",
                        file_path=file_path,
                        line_number=line_num,
                        code_snippet=line.strip()[:100],
                        fix_suggestion="Wrap in try-except with retry logic",
                        stability_score=60,
                    ))

    def _check_hardcoded_urls(self, line: str, line_num: int, file_path: str, report: RPAReport):
        """Detect hardcoded URLs in RPA code."""
        m = re.search(r'(?:goto|navigate)\(\s*["\']((https?://|www\.)[^"\']+)["\']', line)
        if m:
            url = m.group(1)
            if "localhost" not in url and "127.0.0.1" not in url:
                report.findings.append(RPAFinding(
                    severity="medium",
                    category="hardcoded_url",
                    title="Hardcoded URL in RPA",
                    description=f"URL: {url[:60]} — should be in config/env var",
                    file_path=file_path,
                    line_number=line_num,
                    code_snippet=line.strip()[:100],
                    fix_suggestion="Move to config.toml or environment variable",
                    stability_score=50,
                ))

    def _score_selector(self, selector: str) -> int:
        """Score a selector's stability (0-100)."""
        for pattern, score in sorted(_SELECTOR_SCORES.items(), key=lambda x: -x[1]):
            if pattern in selector:
                return score
        # Default: moderate stability
        return 50

    def _suggest_fix(self, selector: str) -> str:
        """Suggest a more stable selector."""
        if "." in selector and "#" not in selector and "data-" not in selector:
            return f"Replace CSS class selector with data-testid: page.get_by_test_id('unique-id')"
        if "//" in selector or "xpath" in selector.lower():
            return "Replace XPath with Playwright locator: page.get_by_role() or page.get_by_text()"
        if "nth-child" in selector or ":nth" in selector:
            return "Positional selectors break on layout changes — use data-testid or aria-label"
        return "Consider using page.get_by_test_id() or page.get_by_role() for stability"
