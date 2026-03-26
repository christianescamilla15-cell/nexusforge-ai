# Contributing to NexusForge AI

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/nexusforge.git`
3. Create a feature branch: `git checkout -b feat/your-feature`
4. Make your changes
5. Push and open a Pull Request against `main`

## Branch Naming

| Prefix | Use |
|---|---|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `refactor/` | Code restructuring without behavior change |
| `docs/` | Documentation only |
| `test/` | Adding or updating tests |
| `chore/` | Build, CI, dependency updates |

Examples: `feat/swarm-mesh-topology`, `fix/workflow-retry-logic`, `docs/adr-006`

## Code Style

### Python (backend)

- Formatter: **black** (line length 88)
- Import sorting: **isort** (profile: black)
- Linting: **ruff**
- Type hints required for all public functions

```bash
black .
isort .
ruff check .
```

### JavaScript (SDK)

- Linting: **eslint** with recommended config
- No semicolons (configured in eslint)
- ES modules (`import/export`)

```bash
cd packages/sdk
npx eslint src/
```

## Testing

### Requirements

- All new features must include tests
- All bug fixes must include a regression test
- Minimum coverage: 80% for new code

### Running tests

```bash
# Backend
docker compose exec api pytest tests/ -v --cov=app

# SDK
cd packages/sdk && npm test
```

## Pull Request Process

1. Ensure all tests pass locally
2. Update documentation if your change affects public APIs
3. Add an entry to the relevant ADR if your change involves an architectural decision
4. Request review from at least one maintainer
5. Squash merge into `main` after approval

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add mesh topology to swarm executor
fix: prevent duplicate workflow step names
docs: add ADR-006 for caching strategy
refactor: extract agent memory into separate module
```
