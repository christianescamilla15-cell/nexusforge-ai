# -*- coding: utf-8 -*-
"""GitFlow governance template generator (Gap 5 from the vision doc).

Emits a drop-in bundle that establishes GitFlow plus the governance
primitives a legacy modernization team needs on day one: CODEOWNERS,
branch protection rules (as a manual setup doc plus GitHub Actions
guards), PR and issue templates, pull request title validation,
and two documented branch strategies running in parallel.

Why two flows?
==============

Real enterprise modernization programs almost always discover two
independent release cadences:

1. **Application flow** — the feature code that ships to end users.
   Classic GitFlow: master (stable) ← develop (integration) ← feature/*.
   Releases cut from develop into release/x.y branches then merge to
   master with a tag.

2. **Infrastructure flow** — the IaC / pipeline code that deploys
   the application. Runs on infra/main directly (no develop stage)
   because every change is independently deployable and rollback
   is handled by Terraform state, not git history.

Mixing these two streams on one branch strategy is a common source
of "we can't deploy because the feature branch isn't ready" blockers.
Splitting them matches the Batch 3 finding from real enterprise
programs. The generated docs explain the contract so every team
member has the same mental model.

Generated layout:

    out_dir/
    ├── .github/
    │   ├── CODEOWNERS
    │   ├── pull_request_template.md
    │   ├── ISSUE_TEMPLATE/
    │   │   ├── bug_report.md
    │   │   └── feature_request.md
    │   └── workflows/
    │       ├── pr-title-check.yml
    │       ├── codeowners-review.yml
    │       └── branch-protection-audit.yml
    ├── docs/
    │   ├── GITFLOW.md
    │   └── BRANCH_PROTECTION.md
    └── README.md

All templates are language-agnostic — no references to .NET, Python
or JavaScript internals. Teams can drop this bundle into any repo.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Result dataclass ───────────────────────────────────────────────────────


@dataclass
class GeneratedGitFlow:
    out_dir: str
    files_written: list[str] = field(default_factory=list)
    workflows_generated: int = 0
    templates_generated: int = 0
    docs_generated: int = 0

    def to_dict(self) -> dict:
        return {
            "out_dir": self.out_dir,
            "files_written": self.files_written,
            "workflows_generated": self.workflows_generated,
            "templates_generated": self.templates_generated,
            "docs_generated": self.docs_generated,
        }


# ── CODEOWNERS ─────────────────────────────────────────────────────────────


_CODEOWNERS = """# CODEOWNERS — per-path review requirements
#
# Syntax: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
#
# Lines are matched bottom-up — the LAST match wins. Keep specific
# overrides at the bottom and broad fallback at the top.

# ── Global fallback ──────────────────────────────────────────────
# Everything not matched below requires at least one maintainer review.
*                                       @CHANGEME-maintainers

# ── Application code ─────────────────────────────────────────────
/backend/                               @CHANGEME-backend-team
/frontend/                              @CHANGEME-frontend-team
/mobile/                                @CHANGEME-mobile-team

# ── Infrastructure and pipelines ─────────────────────────────────
/infrastructure/                        @CHANGEME-platform-team
/terraform/                             @CHANGEME-platform-team
/.github/workflows/                     @CHANGEME-platform-team
/Dockerfile                             @CHANGEME-platform-team
/docker-compose.yml                     @CHANGEME-platform-team
/helm/                                  @CHANGEME-platform-team
/kustomize/                             @CHANGEME-platform-team

# ── Security-sensitive ───────────────────────────────────────────
/backend/app/auth/                      @CHANGEME-security-team
/backend/app/security/                  @CHANGEME-security-team
/backend/app/db/migrations/             @CHANGEME-platform-team @CHANGEME-backend-team
/.github/CODEOWNERS                     @CHANGEME-security-team

# ── Docs ─────────────────────────────────────────────────────────
/docs/                                  @CHANGEME-docs-team
*.md                                    @CHANGEME-docs-team

# Replace every @CHANGEME-* placeholder with a real GitHub team
# slug (e.g. @your-org/backend-core). CODEOWNERS requires that the
# team exists in the org and has write access to the repo, otherwise
# the reviews never resolve and PRs get stuck.
"""


# ── PR + issue templates ───────────────────────────────────────────────────


_PR_TEMPLATE = """## Summary

<!-- 1-2 sentences — what does this change do, not how. -->

## Change type

- [ ] feat — new user-facing capability
- [ ] fix — bug fix
- [ ] chore — maintenance, deps, tooling
- [ ] docs — documentation only
- [ ] refactor — no behavior change
- [ ] perf — measurable performance win
- [ ] test — test coverage
- [ ] security — security improvement

## Breaking changes

- [ ] This PR contains breaking changes
- [ ] This PR requires a database migration
- [ ] This PR requires environment variable updates

## Test plan

<!--
Bulleted checklist of what you tested. "Ran the tests" is not
enough — describe the actual scenarios.
-->

- [ ]
- [ ]

## Screenshots / logs

<!-- For UI changes: before/after. For backend: sample response bodies or log lines. -->

## Checklist

- [ ] PR title follows `type(scope): description` (conventional commits)
- [ ] Updated docs if behavior changed
- [ ] Added or updated tests
- [ ] Confidentiality audit passed (if applicable)
- [ ] Rolled back locally at least once to verify revertability
"""


_BUG_REPORT = """---
name: Bug report
about: Report a reproducible defect
title: 'bug: '
labels: bug
---

## What happened

<!-- A clear and concise description of the bug. -->

## Expected behavior

<!-- What should have happened. -->

## Steps to reproduce

1.
2.
3.

## Environment

- Version / commit SHA:
- Browser / OS (if frontend):
- Backend URL:
- Database:

## Logs and screenshots

<!-- Paste the relevant log excerpt. Redact any secrets. -->
"""


_FEATURE_REQUEST = """---
name: Feature request
about: Propose a new capability
title: 'feat: '
labels: enhancement
---

## Problem statement

<!-- What user problem does this solve? Include the "I was trying to X but..." pattern. -->

## Proposed solution

<!-- High level — not code. -->

## Alternatives considered

<!-- Other approaches you thought about and why they were rejected. -->

## Success criteria

- [ ]
- [ ]

## Scope

- [ ] Backend work required
- [ ] Frontend work required
- [ ] Infrastructure / migration required
- [ ] Docs required
"""


# ── GitHub Actions workflows ───────────────────────────────────────────────


_PR_TITLE_CHECK = """# Enforce conventional commit style on PR titles
# https://www.conventionalcommits.org/

name: PR title check

on:
  pull_request:
    types: [opened, edited, synchronize, reopened]

permissions:
  contents: read
  pull-requests: read

jobs:
  validate:
    name: Validate PR title
    runs-on: ubuntu-latest
    steps:
      - name: Check title format
        env:
          TITLE: ${{ github.event.pull_request.title }}
        run: |
          set -eu
          echo "PR title: $TITLE"
          if ! echo "$TITLE" | grep -qE '^(feat|fix|chore|docs|refactor|perf|test|security|build|ci)(\\([a-z0-9-]+\\))?!?: .+'; then
            echo "::error::PR title must follow conventional commits format: type(scope): description"
            echo "::error::Allowed types: feat, fix, chore, docs, refactor, perf, test, security, build, ci"
            exit 1
          fi
          echo "Title is valid."
"""


_CODEOWNERS_REVIEW = """# Require CODEOWNERS approval before merge
#
# This workflow does NOT grant approvals. It checks that the
# latest review state covers every code owner of the touched paths.
# Configure branch protection to require this workflow + the
# "Require review from Code Owners" setting for belt-and-suspenders.

name: CODEOWNERS review check

on:
  pull_request_review:
    types: [submitted, dismissed]
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]

permissions:
  contents: read
  pull-requests: read

jobs:
  check:
    name: Confirm CODEOWNERS approval
    runs-on: ubuntu-latest
    if: github.event.pull_request.draft == false
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Check code owners
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
        run: |
          set -eu
          gh pr view "$PR_NUMBER" --json reviewDecision --jq '.reviewDecision' > /tmp/decision.txt
          DECISION=$(cat /tmp/decision.txt)
          echo "Review decision: $DECISION"
          if [ "$DECISION" != "APPROVED" ]; then
            echo "::error::PR does not have CODEOWNERS approval yet"
            exit 1
          fi
"""


_BRANCH_PROTECTION_AUDIT = """# Periodic audit of branch protection rules
#
# Runs daily and fails if the protected branches have drifted from
# the documented baseline. Prevents silent weakening of the rules
# by someone clicking around in Settings.

name: Branch protection audit

on:
  schedule:
    - cron: '0 6 * * *'  # 06:00 UTC daily
  workflow_dispatch:

permissions:
  contents: read

jobs:
  audit:
    name: Audit protected branch rules
    runs-on: ubuntu-latest
    steps:
      - name: Check master protection
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -eu
          RULES=$(gh api "repos/${{ github.repository }}/branches/master/protection" 2>&1 || true)
          if echo "$RULES" | grep -q "Not Found"; then
            echo "::error::master has no branch protection rule at all"
            exit 1
          fi
          echo "$RULES" | jq -e '.required_pull_request_reviews.required_approving_review_count >= 1' \\
            || { echo "::error::master requires at least 1 PR review"; exit 1; }
          echo "$RULES" | jq -e '.required_pull_request_reviews.require_code_owner_reviews == true' \\
            || { echo "::error::master must require CODEOWNERS review"; exit 1; }
          echo "$RULES" | jq -e '.enforce_admins.enabled == true' \\
            || { echo "::error::master protection must apply to admins too"; exit 1; }
          echo "$RULES" | jq -e '.required_status_checks' \\
            || { echo "::error::master requires passing status checks"; exit 1; }
          echo "master protection looks good."

      - name: Check develop protection
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -eu
          RULES=$(gh api "repos/${{ github.repository }}/branches/develop/protection" 2>&1 || true)
          if echo "$RULES" | grep -q "Not Found"; then
            echo "::warning::develop has no branch protection rule (only master is enforced)"
            exit 0
          fi
          echo "$RULES" | jq -e '.required_pull_request_reviews.required_approving_review_count >= 1' \\
            || { echo "::error::develop requires at least 1 PR review"; exit 1; }
          echo "develop protection looks good."
"""


# ── Docs ───────────────────────────────────────────────────────────────────


_GITFLOW_DOC = """# GitFlow + dual-branch strategy

This repository runs two independent branch flows in parallel. They
share the `.github/` governance layer (CODEOWNERS, PR templates,
branch protection rules) but otherwise do not mix.

## 1. Application flow

Code that ships to end users. Classic GitFlow.

```
master  <-- stable, tagged releases only
  ^
release/x.y.z  <-- release candidate, bugfixes only
  ^
develop  <-- integration branch, always deployable to staging
  ^
feature/<ticket-slug>  <-- one branch per ticket
```

### Rules

- **feature/**: created off `develop`, merged into `develop` via PR.
  Delete after merge.
- **release/x.y.z**: cut from `develop` when a release is planned.
  Only bugfixes and release notes go here. Merged into `master` at
  release time (creating the release tag) and back-merged into
  `develop` to carry the bugfixes forward.
- **master**: no direct commits. Only receives merges from
  `release/*` or `hotfix/*`. Every merge is a release.
- **hotfix/<ticket>**: created off `master` for emergency production
  fixes. Merged into both `master` (with a patch version bump) and
  `develop`.

### PR path

`feature/*` → `develop` → `release/*` → `master`

Developers never target `master` directly. If you need to, you are
doing a `hotfix/*`, not a feature.

## 2. Infrastructure flow

Code that deploys the application. Terraform, Helm, kustomize,
Kubernetes manifests, CI/CD workflow definitions themselves.

```
infra/main  <-- deployable, every commit is a real apply candidate
  ^
infra/feature/<ticket>  <-- one branch per change
```

### Rules

- **infra/main**: always deployable. No release branches — every
  commit is independently applyable via `terraform apply` or
  `helm upgrade`. Rollback is handled by Terraform state or Helm
  history, not by git revert.
- **infra/feature/**: one branch per change. Merged directly into
  `infra/main` via PR. No integration branch — we rely on Terraform
  plan output + PR review to catch breakage before it lands.

### Why no develop for infrastructure?

Because an infrastructure change is validated by `terraform plan`
and applied against a staging or ephemeral environment **inside the
PR pipeline**, not by being "integrated" on a develop branch first.
The plan output in the PR IS the integration check. Landing it to
`infra/main` then triggers the production apply (or a second-stage
manual approval, depending on environment).

## Handoffs between flows

When an application change requires an infrastructure change:

1. Open two PRs. Link them in their descriptions.
2. The infra PR lands first. Its CI deploys the new infra to
   staging.
3. The app PR depends on the infra PR being merged (enforce via
   a status check, not a manual process).
4. App PR lands, the release branch picks it up, production ships
   both changes on the same release.

If the infra change is not yet urgent, you can sit on it and land
the app PR behind a feature flag. Do NOT land the app change that
requires the infra change before the infra is in place — your CI
will fail at the staging apply step.

## Who enforces this

- **GitHub branch protection rules** — see `docs/BRANCH_PROTECTION.md`
  for the manual setup and `.github/workflows/branch-protection-audit.yml`
  for the automated daily check that the rules have not drifted.
- **CODEOWNERS** — see `.github/CODEOWNERS`. Every path has a team
  that must approve changes; `.github/workflows/codeowners-review.yml`
  guards PRs that try to merge without owner approval.
- **Conventional commit titles** — `.github/workflows/pr-title-check.yml`
  fails the PR if the title does not start with a known type
  (feat / fix / chore / etc.).
"""


_BRANCH_PROTECTION_DOC = """# Branch protection — manual setup

GitHub does not (yet) expose branch protection rules through a
declarative file that lives in the repo. Set the rules up once
per environment via the Settings UI or the `gh api` CLI. The
automated audit workflow (`branch-protection-audit.yml`) checks
these settings daily and fails if they drift.

## master branch rules

Navigate: **Repository → Settings → Branches → Add rule → Branch name pattern: `master`**

Enable the following:

- [x] Require a pull request before merging
  - [x] Require approvals — at least **1** approval
  - [x] Dismiss stale pull request approvals when new commits are pushed
  - [x] Require review from Code Owners
  - [x] Require approval of the most recent reviewable push
- [x] Require status checks to pass before merging
  - [x] Require branches to be up to date before merging
  - Required status checks:
    - `Validate PR title`
    - `Confirm CODEOWNERS approval`
    - (Add your CI pipeline's required checks here)
- [x] Require conversation resolution before merging
- [x] Require signed commits
- [x] Require linear history
- [x] Include administrators
- [x] Restrict who can push to matching branches
  - Add only the release-bot account or a small release team
- [x] Do not allow bypassing the above settings
- [x] Restrict deletions
- [x] Require deployments to succeed before merging (if your
      repo has deployment environments configured)

## develop branch rules

Same as master, with these differences:

- Required approvals: **1** (same)
- Conventional commit PR titles required
- No "Restrict who can push" — the develop branch is meant for
  integration, so anyone on the team with write access should be
  able to push feature branches into it via PR.
- No "Require linear history" — develop can contain merge commits
  from feature branches.

## infra/main branch rules

Tighter than application branches because infra changes are
directly deployable:

- Required approvals: **2**
- Required status checks:
  - `Validate PR title`
  - `Confirm CODEOWNERS approval`
  - `terraform plan` (must have no diff for already-deployed resources)
  - `tflint` / `tfsec` / whatever linters you use
- [x] Include administrators
- [x] Require linear history
- [x] Restrict who can push to matching branches
  - Only the platform team and a release bot

## Quick audit via gh CLI

```bash
gh api repos/:owner/:repo/branches/master/protection
gh api repos/:owner/:repo/branches/develop/protection
gh api repos/:owner/:repo/branches/infra/main/protection
```

The daily audit workflow runs equivalent checks automatically.
If any of them fail, ops gets a GitHub Actions failure email and
the drift is visible in the workflow history.
"""


_README = """# GitFlow governance bundle

Auto-generated by NexusForge. Drop the contents of this bundle
into the root of a repository to establish a dual-flow GitFlow
strategy with the governance primitives required for a
production-ready modernization program.

## What is in this bundle

- `.github/CODEOWNERS` — per-path ownership, enforced on every PR
- `.github/pull_request_template.md` — required PR description
- `.github/ISSUE_TEMPLATE/*.md` — bug and feature issue templates
- `.github/workflows/pr-title-check.yml` — conventional commit enforcement
- `.github/workflows/codeowners-review.yml` — CODEOWNERS approval gate
- `.github/workflows/branch-protection-audit.yml` — daily drift check
- `docs/GITFLOW.md` — the dual-flow branching model explained
- `docs/BRANCH_PROTECTION.md` — manual setup guide for GitHub rules

## What you still need to do

1. **Replace every `@CHANGEME-*` placeholder in CODEOWNERS** with
   real GitHub team slugs. CODEOWNERS requires that the teams
   exist in the org and have write access; otherwise the reviews
   never resolve and PRs get stuck.

2. **Set up branch protection rules manually** in GitHub Settings
   for `master`, `develop`, and `infra/main`. Follow the recipe
   in `docs/BRANCH_PROTECTION.md`. The audit workflow runs daily
   and will fail if any of these drift.

3. **Create the branches** if they do not exist:
   ```bash
   git checkout master
   git checkout -b develop
   git push -u origin develop
   git checkout -b infra/main
   git push -u origin infra/main
   ```

4. **Inform the team** — read `docs/GITFLOW.md` together. The
   dual-flow model only works if everyone understands the contract
   between the application and infrastructure flows.

## Why dual-flow?

Real enterprise modernization programs almost always discover
two independent release cadences: application code ships on a
feature-driven cycle, while infrastructure code (Terraform, Helm,
CI definitions) ships per-commit because rollback is handled at
the deployment layer. Mixing them on one branch strategy causes
"we can't deploy because the feature branch isn't ready"
blockers. Splitting them matches what actually happens in the
field. See `docs/GITFLOW.md` for the full explanation.

## Why a daily audit?

Branch protection rules live in GitHub's settings UI, not in the
repo, so they can be weakened silently by anyone with admin
rights. The `branch-protection-audit.yml` workflow runs at 06:00
UTC every day and fails if the rules have drifted from the
documented baseline. Drift shows up in the GitHub Actions history
and can be wired to Slack or email.

_Generated by NexusForge GitFlow template generator. Not real
client data. Replace all placeholders before using in a real repo._
"""


# ── Public entry point ─────────────────────────────────────────────────────


def generate_gitflow_bundle(out_dir: Path) -> GeneratedGitFlow:
    """Write the full GitFlow governance bundle to out_dir.

    Idempotent: overwrites existing files. Safe to re-run on an
    existing bundle to pick up template updates.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    github_dir = out_dir / ".github"
    workflows_dir = github_dir / "workflows"
    issue_dir = github_dir / "ISSUE_TEMPLATE"
    docs_dir = out_dir / "docs"
    for d in (github_dir, workflows_dir, issue_dir, docs_dir):
        d.mkdir(parents=True, exist_ok=True)

    result = GeneratedGitFlow(out_dir=str(out_dir))

    # Governance files
    files: list[tuple[Path, str, str]] = [
        (github_dir / "CODEOWNERS", _CODEOWNERS, "codeowners"),
        (github_dir / "pull_request_template.md", _PR_TEMPLATE, "template"),
        (issue_dir / "bug_report.md", _BUG_REPORT, "template"),
        (issue_dir / "feature_request.md", _FEATURE_REQUEST, "template"),
        (workflows_dir / "pr-title-check.yml", _PR_TITLE_CHECK, "workflow"),
        (workflows_dir / "codeowners-review.yml", _CODEOWNERS_REVIEW, "workflow"),
        (workflows_dir / "branch-protection-audit.yml", _BRANCH_PROTECTION_AUDIT, "workflow"),
        (docs_dir / "GITFLOW.md", _GITFLOW_DOC, "doc"),
        (docs_dir / "BRANCH_PROTECTION.md", _BRANCH_PROTECTION_DOC, "doc"),
        (out_dir / "README.md", _README, "doc"),
    ]

    for path, content, kind in files:
        path.write_text(content, encoding="utf-8")
        rel = str(path.relative_to(out_dir)).replace("\\", "/")
        result.files_written.append(rel)
        if kind == "workflow":
            result.workflows_generated += 1
        elif kind == "template":
            result.templates_generated += 1
        elif kind == "doc":
            result.docs_generated += 1

    return result
