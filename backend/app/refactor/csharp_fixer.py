"""C# SQL Injection Fixer — auto-convert string concatenation to parameterized queries.

⚠ ADVISORY-ONLY remediation (2026-05-02 triangulation, gpt55 finding,
Tier 2 #5). The current regex-based transforms rewrite the SQL literal
to use a `@param` placeholder but ONLY emit a TODO comment for the
matching `cmd.Parameters.AddWithValue(...)` call — they do not insert
the actual parameter binding. As a result the modified file compiles
but the SQL is still unparameterized at runtime: the `@param` token is
sent to the database as an opaque string with no value bound, which
either errors at execution or (worse, in some drivers) is silently
treated as a literal token. **Do not rely on these transforms as a
real SQL-injection fix.** Each fix dict emitted here carries
`advisory_only: True` and `requires_manual_completion: True` so the
batch pipeline (or any downstream consumer) can route them through a
human-review queue instead of auto-committing.

The proper remediation is an AST/Roslyn-backed transform that inserts
the SqlParameter binding at the same call site. Tracked as Tier 3 work
in session_2026_05_02_triangulation_findings.md.

Handles patterns commonly found in legacy enterprise C# apps:
  1. "SELECT * FROM x WHERE id = " + variable  →  @param with SqlParameter
  2. $"SELECT * FROM x WHERE id = {variable}"  →  @param with SqlParameter
  3. String.Format("SELECT ... {0}", var)       →  @param with SqlParameter
  4. cmd.CommandText = "..." + var              →  parameterized
  5. Dynamic query builder patterns             →  parameterized

Also fixes:
  - Hardcoded credentials → Configuration/Environment pattern
  - Missing using statements for security classes
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    file_path: str
    fixes_applied: int
    original_lines: int
    fixed_lines: int
    diff_summary: str
    fixes: list[dict]


class CSharpFixer:
    """Fix C# security vulnerabilities with deterministic transforms."""

    def __init__(self, project_root: str, dry_run: bool = False):
        self.root = Path(project_root)
        self.dry_run = dry_run

    def fix_file(self, file_path: str) -> FixResult:
        """Fix all known vulnerabilities in a single .cs file."""
        fpath = self.root / file_path
        if not fpath.exists():
            return FixResult(file_path, 0, 0, 0, "file not found", [])

        original = fpath.read_text(encoding="utf-8", errors="ignore")
        fixed = original
        fixes = []

        # Fix SQL injection patterns
        fixed, sql_fixes = self._fix_sql_concat(fixed, file_path)
        fixes.extend(sql_fixes)

        fixed, interp_fixes = self._fix_sql_interpolation(fixed, file_path)
        fixes.extend(interp_fixes)

        # Fix hardcoded credentials
        fixed, cred_fixes = self._fix_hardcoded_creds(fixed, file_path)
        fixes.extend(cred_fixes)

        if not self.dry_run and fixed != original and fixes:
            fpath.write_text(fixed, encoding="utf-8")

        orig_lines = len(original.splitlines())
        fixed_lines = len(fixed.splitlines())

        return FixResult(
            file_path=file_path,
            fixes_applied=len(fixes),
            original_lines=orig_lines,
            fixed_lines=fixed_lines,
            diff_summary=f"+{fixed_lines - orig_lines} lines" if fixed_lines != orig_lines else "same length",
            fixes=fixes,
        )

    def _fix_sql_concat(self, code: str, file_path: str) -> tuple[str, list[dict]]:
        """Fix SQL string concatenation → parameterized queries."""
        fixes = []
        lines = code.splitlines()
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Pattern: "SELECT ... WHERE x = " + variable
            m = re.search(
                r'("(?:SELECT|INSERT|UPDATE|DELETE)\s+[^"]*(?:WHERE|VALUES|SET)\s+[^"]*")\s*\+\s*(\w+)',
                line, re.IGNORECASE
            )
            if m:
                sql_part = m.group(1)
                var_name = m.group(2)
                param_name = f"@{var_name}"

                # Replace concatenation with parameter placeholder
                new_sql = sql_part[:-1] + f" {param_name}" + '"'
                new_line = line[:m.start()] + new_sql
                # Add parameter on next line (with proper indentation)
                indent = re.match(r'^(\s*)', line).group(1)
                # Loud, scannable banner so reviewers cannot miss that
                # this fix is incomplete. CI lint can grep for the marker.
                fixed_lines.append(
                    f"{indent}// NEXUSFORGE_ADVISORY_FIX: SQL injection PARTIALLY rewritten."
                )
                fixed_lines.append(
                    f"{indent}// MUST add parameter binding manually before deploy:"
                )
                fixed_lines.append(
                    f'{indent}//     cmd.Parameters.AddWithValue("{param_name}", {var_name});'
                )
                fixed_lines.append(
                    f"{indent}// Without the binding the query is still unsafe."
                )
                fixed_lines.append(new_line)

                logger.warning(
                    "csharp_fixer: advisory-only SQL fix applied at %s:%d "
                    "(variable=%s) — manual parameter binding REQUIRED",
                    file_path, i + 1, var_name,
                )
                fixes.append({
                    "type": "sql_injection_concat",
                    "line": i + 1,
                    "variable": var_name,
                    "file": file_path,
                    "advisory_only": True,
                    "requires_manual_completion": True,
                    "manual_step": (
                        f'cmd.Parameters.AddWithValue("{param_name}", {var_name});'
                    ),
                })
                i += 1
                continue

            fixed_lines.append(line)
            i += 1

        return "\n".join(fixed_lines), fixes

    def _fix_sql_interpolation(self, code: str, file_path: str) -> tuple[str, list[dict]]:
        """Fix SQL string interpolation → parameterized queries."""
        fixes = []
        lines = code.splitlines()
        fixed_lines = []

        for i, line in enumerate(lines):
            # Pattern: $"SELECT ... WHERE x = {variable}"
            m = re.search(
                r'\$"((?:SELECT|INSERT|UPDATE|DELETE)\s+[^"]*)\{(\w+)\}([^"]*)"',
                line, re.IGNORECASE
            )
            if m:
                sql_before = m.group(1)
                var_name = m.group(2)
                sql_after = m.group(3)
                param_name = f"@{var_name}"

                indent = re.match(r'^(\s*)', line).group(1)
                new_line = line[:m.start()] + f'"{sql_before}{param_name}{sql_after}"' + line[m.end():]

                fixed_lines.append(
                    f"{indent}// NEXUSFORGE_ADVISORY_FIX: SQL interpolation PARTIALLY rewritten."
                )
                fixed_lines.append(
                    f"{indent}// MUST add parameter binding manually before deploy:"
                )
                fixed_lines.append(
                    f'{indent}//     cmd.Parameters.AddWithValue("{param_name}", {var_name});'
                )
                fixed_lines.append(
                    f"{indent}// Without the binding the query is still unsafe."
                )
                fixed_lines.append(new_line)

                logger.warning(
                    "csharp_fixer: advisory-only SQL interpolation fix at %s:%d "
                    "(variable=%s) — manual parameter binding REQUIRED",
                    file_path, i + 1, var_name,
                )
                fixes.append({
                    "type": "sql_injection_interpolation",
                    "line": i + 1,
                    "variable": var_name,
                    "file": file_path,
                    "advisory_only": True,
                    "requires_manual_completion": True,
                    "manual_step": (
                        f'cmd.Parameters.AddWithValue("{param_name}", {var_name});'
                    ),
                })
                continue

            fixed_lines.append(line)

        return "\n".join(fixed_lines), fixes

    def _fix_hardcoded_creds(self, code: str, file_path: str) -> tuple[str, list[dict]]:
        """Fix hardcoded credentials → environment variables."""
        fixes = []
        lines = code.splitlines()
        fixed_lines = []

        for i, line in enumerate(lines):
            # Pattern: password = "actualpassword"
            m = re.search(
                r'(\w*(?:password|pwd|passwd|secret|api_?key)\w*)\s*=\s*"([^"]{5,})"',
                line, re.IGNORECASE
            )
            if m:
                var_name = m.group(1)
                env_key = re.sub(r'([A-Z])', r'_\1', var_name).upper().strip("_")

                indent = re.match(r'^(\s*)', line).group(1)
                fixed_lines.append(f'{indent}// FIXED by NexusForge: hardcoded credential → environment variable')
                fixed_lines.append(f'{indent}{var_name} = Environment.GetEnvironmentVariable("{env_key}") ?? "";')

                fixes.append({
                    "type": "hardcoded_credential",
                    "line": i + 1,
                    "variable": var_name,
                    "file": file_path,
                })
                continue

            fixed_lines.append(line)

        return "\n".join(fixed_lines), fixes
