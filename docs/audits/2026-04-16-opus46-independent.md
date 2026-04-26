# Independent Audit -- NexusForge AI (13 commits)

**Auditor**: Claude Opus 4.6 (independent, zero prior context)
**Date**: 2026-04-16
**HEAD at audit time**: `89ec5e8` "fix(routes): Codex audit fixes"
**Scope**: 13 commits from `9d74458` (Gap F discovery_loader) through `89ec5e8`

> **Confidentiality note (2026-04-25)**: this is the *scrubbed* version
> of the original `AUDIT-REPORT-v2.md` produced at the repo root. All
> real client / vendor / regulator / exchange names have been replaced
> with the same codename mapping the F-02 fix applied to source files.
> See the [Remediation status](#remediation-status) section below for
> which commits closed which findings.

---

## Remediation status

| Finding | Severity | Status | Closed by |
|---|---|---|---|
| F-01 CWE-only hijack | CRITICAL | **CLOSED** | `f4bc003` (2026-04-25) |
| F-02 codename leaks | CRITICAL | **CLOSED** | `43b67c1` (2026-04-25) |
| F-03 fuzzy codename match | HIGH | open | -- |
| F-04 risk boost position bias | HIGH | open | -- |
| F-05 should_filter() drops accepted-risk criticals | HIGH | open | -- |
| F-06 /ecosystem endpoint rate limit | MEDIUM | open | -- |
| F-07 Spanish ITGC narrative | MEDIUM | partially closed by F-02 scrub (banner restored) | -- |
| F-08 Mythos WAF downgrade chaining | MEDIUM | open | -- |
| F-09 `_Path` import alias | LOW | open | -- |
| F-10 forward-declared classes | LOW | open | -- |
| F-11 escapeHtml backtick injection | LOW | not exploitable today | -- |

---

## Verification Results

| Check | Expected | Actual | Status |
|---|---|---|---|
| Tests | ~780 passed | **780 passed** | PASS |
| Mythos self-scan | 0 findings | **0 findings, 135 filtered** | PASS |
| Discovery loader | loads corpus | **195 findings, 29 blockers, 9 apps** | PASS |
| `str(exc)` leaks in routes | 0 | **0** | PASS |
| Rate limit coverage | >40 calls | **46 calls** | PASS |
| Codename leaks | 0 files | **7 non-test files** | **FAIL → fixed in `43b67c1`** |

---

## Scores

| Category | Score (1-5) | Notes |
|---|---|---|
| Security | **4** | str(exc) leaks fixed, rate limits on all exec endpoints, Mythos self-scan clean. One CWE-match logic bug (see F-01). |
| Quality | **4** | Clean architecture, dataclasses well-structured, comprehensive test coverage (780). Profile loader is robust against malformed YAML. |
| Correctness | **3** | CWE-only hijack bug contradicts docstring. Fuzzy codename matching can produce wrong-app matches. Risk boost only hits first medium phase. |
| Completeness | **4** | All 13 commits deliver stated features. Discovery loader, ecosystem metrics, profile priors all wired. Frontend cards render all new data. |
| Codenames | **1** | 7 non-test files contained real company/product names. File header claimed "NO real client data" -- false. |
| Architecture | **5** | Excellent layering: calibration is read-only, profile is optional (no-op when absent), narrative enrichment is idempotent, all priors compose cleanly. |

**Weighted average: 3.5 / 5**

---

## Critical Findings

### F-01 [CRITICAL] -- CWE-only match hijack in baseline_calibration.py

**File**: `backend/app/security/baseline_calibration.py:215-220` (pre-fix)

The docstring at line 196-198 explicitly documents a guard:

> hit (only if pattern_match is empty OR one of its patterns also appears in the haystack -- prevents CWE-only hijack)

**The code did NOT implement this guard.** The CWE branch at line 219 returned immediately on CWE match without checking `pattern_match`:

```python
for e in candidates:
    if e.cwe and e.cwe.upper().replace(" ", "") == cwe_norm:
        return self._build_match(e)  # <-- no pattern_match check
```

**Impact**: A finding with CWE-798 (hardcoded creds) in `routes/auth.py` could incorrectly match a baseline entry for CWE-798 in `synth/vulnerabilities/hardcoded_creds.py`, getting silently filtered as "by-design" when it's a real vulnerability.

**Fix shipped (`f4bc003`)**: implemented the documented guard:

```python
if e.cwe and e.cwe.upper().replace(" ", "") == cwe_norm:
    if not e.pattern_match or any(p.lower() in haystack for p in e.pattern_match):
        return self._build_match(e)
```

Plus regression test `test_cwe_only_match_does_not_hijack_when_no_pattern_present` and a companion test verifying the empty-pattern_match escape hatch still works.

### F-02 [CRITICAL] -- Real company names in 7 production files

The initial grep for `[client-codename]|platform-vendor` found 2 files. A broader search revealed **real company/product names** scattered across 7 non-test source files:

| File | Leaks |
|---|---|
| `app/synth/fixtures/tenant_alpha.yaml` | platform-vendor, cliente, audit-firm, idp-provider, grc-tool, exchange, industry-body, external-settlement-portal, praxis-ecosystem (11+ instances) |
| `app/synth/profile.py` | platform-vendor (line 503), app-01 (line 585), external-settlement-portal (line 607) |
| `app/synth/fixtures/tenant-alpha-ecosystem-health.yaml` | (not read, but flagged by grep) |
| `app/refactor/discovery_loader.py` | (flagged by grep) |
| `app/refactor/pii_scanner.py` | (flagged by grep) |
| `app/refactor/strangler_planner.py` | (flagged by grep) |
| `app/security/baselines/tenant-alpha-vulns-baseline.yaml` | (flagged by grep) |

(Above table shows the **post-fix** values; the pre-fix scan found the corresponding real names.)

**tenant_alpha.yaml line 4** explicitly claimed: *"This file is committed to the repo but contains NO real client data."* This was provably false at audit time.

Notable leaks (pre-fix):
- Line 37: identified the client's stock exchange listings
- Line 42: named the auditor
- Line 43: named internal tools (GRC + IdP)
- Line 670: named both the client and the platform vendor
- Line 680: named the internal platform

**This was the single most dangerous finding in this audit.** If the repo were ever shared with a prospect, open-sourced, or accessed by a pentester, the leaked names would immediately identify the real client engagement.

**Fix shipped (`43b67c1`)**: scrubbed all flagged strings using the codename mapping below; renamed 3 baseline IDs (`sicofav-* → app-01-*`); added docstrings to `discovery_loader._app_codename_from_label` + `_domain_from_sheet_name` documenting that the remaining string matchers are external-deliverable parser inputs, never internal classifications. Post-fix grep across `backend/app/`: 2 hits remain, both in those documented input matchers.

---

## High Findings

### F-03 [HIGH] -- Fuzzy codename matching produces wrong-app matches

**Files**: `strangler_planner.py:791-802`, `strangler_planner.py:723-735`

The discovery context and ecosystem metrics use substring matching:

```python
for candidate in self._discovery.apps_mentioned:
    if candidate.lower() in app_name or app_name in candidate.lower():
        codename = candidate
        break
```

**Problem**: An app named `"app-0"` matches `"app-01"`, `"app-02"`, etc. -- always returning the first one found. An app named `"praxis"` matches `"praxis-ecosystem"`. The match is order-dependent and non-deterministic (depends on iteration order of `apps_mentioned`).

**Impact**: Wrong discovery findings attached to the wrong app's plan. Risk boosts applied to incorrect phases.

**Fix**: Require exact match first, then fall back to substring only if the substring match is unambiguous (single result).

### F-04 [HIGH] -- Risk boost only hits first medium-risk phase

**File**: `strangler_planner.py:829-844`

```python
if plan.discovery_blockers and plan.phases:
    for phase in plan.phases:
        if phase.risk == "medium":
            phase.risk = "high"
            ...
            break  # only boost one phase
```

If the first phase is already "high", it gets an annotation and the loop breaks. If phases 2-5 are "medium" with relevant blockers, they are never boosted. The boost is position-biased, not relevance-biased.

### F-05 [HIGH] -- should_filter() silently drops accepted-risk criticals

**File**: `baseline_calibration.py:247-266`

```python
if status in ("by-design", "accepted-risk", "false-positive"):
    return True  # filter regardless of severity
```

A CRITICAL finding marked "accepted-risk" is filtered identically to an INFO finding. The docstring acknowledges this is policy, but the policy is dangerous: one wrong `accepted-risk` tag on a critical finding = invisible vulnerability.

**Recommendation**: At minimum, log a WARNING when filtering critical-severity accepted-risk entries so they appear in scan logs even if filtered from the report.

---

## Medium Findings

### F-06 [MEDIUM] -- /ecosystem endpoint lacks rate limiting

**File**: `backend/app/routes/refactor.py:1113`

The `/showcase/{tenant_id}/ecosystem` endpoint is public (no auth) and loads YAML files + instantiates dataclasses on every request. No rate limiting, no caching. An attacker can abuse it to cause repeated filesystem I/O.

All other showcase endpoints have the same pattern (public, no rate limit), but `/ecosystem` is the heaviest because it loads 2 separate YAML files.

### F-07 [MEDIUM] -- tenant_alpha.yaml compliance narrative in Spanish

**File**: `tenant_alpha.yaml:41-47`

The compliance narrative contains untranslated Spanish text with real process names: `"seguridad logica, control de cambios, jobs, respaldos, DRP, politicas, segregacion de funciones, recertificacion de accesos, segregacion de ambientes, ITACs"`. While individually these are generic ITGC control names, together with exchange-listing + audit-firm references they used to narrow identification to a single client.

(Partially mitigated by the F-02 scrub that removed the surrounding identifiers; the Spanish narrative itself remains.)

### F-08 [MEDIUM] -- Mythos WAF downgrade is one-step only

**File**: `mythos.py:206,235`

```python
severity_down = {"critical": "high", "high": "medium", "medium": "low"}
```

A critical SQLi finding behind a WAF becomes "high" -- reasonable. But a WAF is not a fix. If the WAF is misconfigured or bypassed, the critical vulnerability is still there. The downgrade should cap at one level (never critical->medium via chained rules) and the annotation should be more prominent.

Currently, profile calibration runs AFTER baseline calibration (line 350-352 in `full_scan`), so in theory both could chain and produce a double-downgrade. The `[WAF-mitigated]` idempotency guard prevents re-application but doesn't prevent baseline+profile stacking.

---

## Low Findings

### F-09 [LOW] -- `_Path` import alias in refactor.py

**File**: `refactor.py:482,509,629`

Several endpoints import `from pathlib import Path as _Path` inside the function body to avoid shadowing the module-level `Path` (which doesn't exist). This works but is inconsistent -- some endpoints use it, others import `Path` directly (line 1142).

### F-10 [LOW] -- profile.py AppRecipe references forward-declared classes

**File**: `profile.py:278-279`

`AppRecipe` at line 278-279 references `ExposureProfile` and `RegionalPolicy` as type annotations, but these classes are defined AFTER `AppRecipe` (lines 568 and 597). This works because of `from __future__ import annotations` at line 9, but makes the file harder to read top-down.

### F-11 [LOW] -- escapeHtml regex doesn't handle backtick injection

**File**: `TenantShowcase.jsx:969-977`

`escapeHtml()` covers the standard 5 HTML entities. The `inline()` function then processes backtick-delimited code spans. An input containing a backtick followed by HTML could potentially create a `<code>` tag wrapping unescaped content -- but since escapeHtml runs first, the content inside the backtick span is already entity-escaped. **Not exploitable in current flow**, but fragile if the processing order ever changes.

---

## Baseline YAML Entry-by-Entry Review

| ID | Category | Status | Verdict |
|---|---|---|---|
| fp-asyncio-subprocess-exec | injection | accepted-risk | **CORRECT** -- `create_subprocess_exec` is argv-list, not shell |
| fp-synth-vulnerabilities-generator | secrets | by-design | **CORRECT** -- intentional fixture generator |
| fp-test-sqli-fixtures | injection | by-design | **CORRECT** -- test canaries |
| fp-synth-output-generated-code | secrets | by-design | **CORRECT** -- synth output with "synth-fake-*" prefixes |
| fp-k8s-template-placeholders | secrets | by-design | **CORRECT** -- "REPLACE_WITH_REAL_KEY" |
| fp-postgres-dsn-quote-plus | secrets | accepted-risk | **CORRECT** -- quote_plus prevents URL injection |
| fp-csharp-fixer-comment-pattern | secrets | by-design | **CORRECT** -- regex pattern in comment |
| fp-public-health-endpoints | auth | by-design | **CORRECT** -- liveness probes |
| fp-public-metrics-endpoints | auth | by-design | **CORRECT** -- Prometheus scrape |
| fp-public-showcase-endpoints | auth | by-design | **CORRECT** -- public demo |
| fp-public-examples-health-subroutes | auth | by-design | **CORRECT** -- sample data |
| fp-login-endpoint-pre-auth | auth | by-design | **CORRECT** -- OAuth callback is pre-auth |
| ar-jwt-hs256-symmetric | crypto | accepted-risk | **ACCEPTABLE** -- single-issuer, RS256 tracked |
| ar-no-refresh-token | crypto | accepted-risk | **ACCEPTABLE** -- short-session app, revisit if UX changes |
| ar-localstorage-auth-token | data | accepted-risk | **ACCEPTABLE** -- known XSS trade-off, documented |
| info-fernet-upgrade-log | crypto | by-design | **CORRECT** -- marker only |
| ar-tenant-showcase-rendermarkdown | injection | accepted-risk | **CORRECT** -- escapeHtml + whitelist defense-in-depth |

**Verdict**: All 17 baseline entries are legitimate. No entry masks a finding that should be a fix. The accepted-risk entries are well-documented with rationale.

---

## Recommendations

1. **[BLOCKER -- DONE in `43b67c1`]** Scrub all real names from source files. Replacement mapping used: real-vendor → "platform-vendor", real-client → "cliente", real-auditor → "audit-firm", real-idp → "idp-provider", real-grc → "grc-tool", listing exchanges → "exchange", industry body → "industry-body", external settlement portal → "external-settlement-portal", internal ecosystem → "praxis-ecosystem" (already used elsewhere), product-codename → "app-01". Full repo grep ran after scrubbing -- only documented input matchers remain.

2. **[BLOCKER -- DONE in `f4bc003`]** Fix the CWE-only match bug (F-01). Implementation matches docstring. Regression test added: a finding with CWE-798 in a non-synth code path no longer matches the synth-vulnerabilities baseline entry purely on CWE collision.

3. **[HIGH -- open]** Replace substring codename matching with exact-then-fuzzy. First try exact match. If no exact match, try substring but require uniqueness (if 2+ candidates match, return None and log a warning).

4. **[MEDIUM -- open]** Add a WARNING log when filtering critical/high accepted-risk findings. Don't change the filter policy, but make it visible in logs.

5. **[LOW -- open]** Add a simple cache or rate-limit to `/showcase/*/ecosystem`. Even a 60-second in-memory cache would prevent abuse.

---

## Verdict (at audit time, 2026-04-16)

# SHIP-WITH-FIXES

The 13 commits delivered substantial and well-architected features: discovery loader, ecosystem metrics, profile-aware calibration, 7 new dataclasses, frontend cards, and a clean Mythos self-scan. Test coverage was excellent (780 tests), code quality was high, and the security posture (rate limits, str(exc) removal, Fernet encryption) was solid.

**Two blockers had to be fixed before any external visibility:**

1. **F-02 (codename leaks)** -- closed by `43b67c1` (2026-04-25).
2. **F-01 (CWE match bug)** -- closed by `f4bc003` (2026-04-25).

Both fixes were straightforward. After remediation: 813 tests passing, post-fix grep clean, `master` ready for external review.
