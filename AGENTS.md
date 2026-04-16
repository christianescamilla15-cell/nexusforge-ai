# NexusForge AI — Agent Instructions

## What is this repo?

Enterprise AI platform for agent orchestration + automated code remediation.
Handles 5.6M LOC, 189K issues, 3K+ SQL injections across 31 apps for a
publicly-traded enterprise client (codename: `tenant-alpha`).

## Architecture (backend)

```
backend/
├── app/
│   ├── agents/          # 24 AI agents with per-agent model routing
│   ├── auth/            # JWT + Google OAuth + Stripe billing + rate limiting
│   ├── connectors/      # PostgreSQL, MongoDB, Redis connectors
│   ├── refactor/        # Refactoring engine (enterprise scale)
│   │   ├── discovery_loader.py    # Gap F — corpus → DiscoveryIndex (184 findings)
│   │   ├── strangler_planner.py   # Strangler-pattern migration planner (4 priors)
│   │   ├── csharp_analyzer.py     # C# static analysis
│   │   ├── ingestion.py           # Repo → ProjectGraph (2.4s for 616 files)
│   │   └── ...                    # 15+ refactor modules
│   ├── security/
│   │   ├── mythos.py              # Internal security scanner (9 categories)
│   │   ├── baseline_calibration.py # Calibration against known findings
│   │   └── baselines/             # YAML baselines (tenant-alpha + self-scan)
│   ├── synth/
│   │   ├── profile.py             # 14 dataclasses modeling tenant-alpha
│   │   ├── ecosystem_metrics.py   # Ecosystem health KPIs loader
│   │   ├── generator.py           # Synthetic tenant code generator
│   │   └── fixtures/              # tenant_alpha.yaml + ecosystem health YAML
│   └── routes/            # FastAPI endpoints
├── tests/                 # 780+ tests (pytest)
└── run_mythos_self_scan.py  # Calibrated security self-scan runner
```

## Key modules added recently (last 13 commits)

### Security
- `baseline_calibration.py` — loads YAML baselines, matches findings by CWE + pattern + file_path, filters FPs
- `mythos.py` extensions — post-scan calibration hooks (_apply_baseline_calibration + _apply_profile_calibration)
- `baselines/nexusforge-self-scan-baseline.yaml` — 12 FP filters + 5 accepted-risk entries for self-scan
- `baselines/tenant-alpha-vulns-baseline.yaml` — 15 entries + 3 mitigations for client apps

### Refactoring
- `discovery_loader.py` — parses corpus pipeline (MD + xlsx) → DiscoveryIndex
- `strangler_planner.py` — accepts 4 priors: discovery, ecosystem, recipe, and decision-gate

### Synth Profile (7 new dataclasses)
- ExposureProfile, EdgeSecurity, SecretManagement, MultiRobotPipeline
- OperationalProfile, RegionalPolicy, LegalRisk
- Decision-gate extension on RefactorDecision

### Frontend
- TenantShowcase.jsx — EcosystemHealthCard with WAF/Vault/NDA/density
- renderMarkdown with escapeHtml() defense-in-depth

## How to run tests

```bash
cd backend
python -m pytest tests/ -q
```

## How to run Mythos self-scan

```bash
cd backend
python run_mythos_self_scan.py
```
Expected: 0 findings, ~139 filtered.

## Codename convention

Real names NEVER appear in code. Mapping:
- Client airline → `tenant-alpha` or `cliente`
- Platform vendor → `platform-vendor`
- Audit vendor → `audit-vendor`
- Consulting partner → `eng-partner`
