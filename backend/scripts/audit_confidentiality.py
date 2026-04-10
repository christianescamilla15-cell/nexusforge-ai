"""Confidentiality audit — scans the working tree for forbidden terms.

Blocklist is read from a local-only file (never committed). Default path:
  <repo_root>/.confidential/blocklist.txt
Override with env var NEXUSFORGE_CONFIDENTIAL_BLOCKLIST.

Usage:
  python backend/scripts/audit_confidentiality.py           # scan repo root
  python backend/scripts/audit_confidentiality.py path/dir  # scan subtree
  python backend/scripts/audit_confidentiality.py --staged  # scan only staged files

Exit codes:
  0 = clean
  1 = violations found
  2 = blocklist missing or invalid
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BLOCKLIST = REPO_ROOT / ".confidential" / "blocklist.txt"

SKIP_DIRS = {
    ".git",
    ".confidential",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".vercel",
    ".terraform",
    "frontend/dist",
    "frontend/node_modules",
    ".kiro",
}
SKIP_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".exe",
    ".bin",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".mp3",
    ".lock",
}


def load_blocklist(path: Path) -> list[str]:
    if not path.exists():
        print(f"ERROR: blocklist not found at {path}", file=sys.stderr)
        print(
            "Create .confidential/blocklist.txt or set "
            "NEXUSFORGE_CONFIDENTIAL_BLOCKLIST.",
            file=sys.stderr,
        )
        sys.exit(2)
    terms: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        terms.append(line.lower())
    if not terms:
        print(f"ERROR: blocklist at {path} is empty", file=sys.stderr)
        sys.exit(2)
    return terms


def build_pattern(terms: list[str]) -> re.Pattern[str]:
    # Word-boundary match, case-insensitive. Escape each term; allow spaces
    # inside multi-word terms.
    escaped = [re.escape(t) for t in terms]
    # Use lookarounds for soft word boundaries that also work with Unicode.
    pattern = r"(?<![\w])(?:" + "|".join(escaped) + r")(?![\w])"
    return re.compile(pattern, re.IGNORECASE)


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        # Prune skipped directories
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_DIRS
            and f"{rel_dir}/{d}".lstrip("/") not in SKIP_DIRS
        ]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in SKIP_SUFFIXES:
                continue
            files.append(p)
    return files


def iter_staged_files(root: Path) -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            cwd=root,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: could not list staged files via git", file=sys.stderr)
        sys.exit(2)
    files: list[Path] = []
    for line in out.splitlines():
        p = root / line.strip()
        if not p.exists() or p.is_dir():
            continue
        if p.suffix.lower() in SKIP_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        files.append(p)
    return files


def scan(files: list[Path], pattern: re.Pattern[str]) -> list[tuple[Path, int, str, str]]:
    hits: list[tuple[Path, int, str, str]] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            m = pattern.search(line)
            if m:
                hits.append((f, lineno, m.group(0), line.strip()))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=str(REPO_ROOT),
        help="Path to scan (default: repo root)",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Scan only files staged for commit",
    )
    parser.add_argument(
        "--blocklist",
        default=os.environ.get(
            "NEXUSFORGE_CONFIDENTIAL_BLOCKLIST", str(DEFAULT_BLOCKLIST)
        ),
        help="Path to blocklist file",
    )
    args = parser.parse_args()

    blocklist_path = Path(args.blocklist).expanduser().resolve()
    terms = load_blocklist(blocklist_path)
    pattern = build_pattern(terms)

    root = Path(args.path).resolve()
    if args.staged:
        files = iter_staged_files(REPO_ROOT)
        scope = "staged files"
    else:
        files = iter_files(root)
        scope = str(root)

    hits = scan(files, pattern)
    if not hits:
        print(f"OK: confidentiality audit clean ({len(files)} files, {scope})")
        return 0

    print(f"BLOCKED: {len(hits)} confidentiality violation(s) in {scope}")
    for f, lineno, term, excerpt in hits:
        rel = f.relative_to(REPO_ROOT) if REPO_ROOT in f.parents or f == REPO_ROOT else f
        print(f"  {rel}:{lineno}: '{term}' -> {excerpt[:120]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
