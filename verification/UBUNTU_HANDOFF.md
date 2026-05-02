# Ubuntu handoff — opening a new Claude Code session

This doc captures the cross-machine context transfer for migrating the
NexusForge dev/verification flow from Windows to Ubuntu. It exists in
the repo so a fresh Claude Code session opened on Ubuntu in
`/home/chris/nexusforge-ai` finds it via `git pull` even before the
auto-memory directory is populated.

## What you should do FIRST in the new Ubuntu session

```bash
# 1. Confirm you're in the right cwd
pwd     # should be /home/chris/nexusforge-ai
git rev-parse --abbrev-ref HEAD   # master

# 2. Sync with origin (needs auth — see "Blocker 1" below if it fails)
git fetch origin
git status -sb
git pull origin master --ff-only
```

If the pull fails with `could not read Username for github.com`,
that's Blocker 1 below.

## Three blockers carried over from the previous Ubuntu session

### Blocker 1 — `gh` not authenticated for git pulls

Two equally-valid fixes, pick whichever has less friction:

**A. PAT inline (no apt install needed)**

1. Open https://github.com/settings/tokens/new
2. Note: `nexusforge-ubuntu`, expiry 90d, scope: ONLY `repo`
3. Generate, copy the `ghp_...` token

```bash
TOKEN="ghp_..."   # paste yours
git remote set-url origin "https://christianescamilla15-cell:${TOKEN}@github.com/christianescamilla15-cell/nexusforge-ai.git"
git pull origin master
# Strip the token back out so it doesn't sit in git config:
git remote set-url origin https://github.com/christianescamilla15-cell/nexusforge-ai.git
unset TOKEN
```

**B. gh CLI (one-time install needs sudo password)**

```bash
sudo apt install -y gh
gh auth login --git-protocol https
# Browser flow: paste the device code GitHub gives you
git pull origin master
```

### Blocker 2 — `pip install aios-kiro-master` blocked by sandbox

The package is real (PyPI HTTP 200, author = `christianescamilla15@gmail.com`).
The Ubuntu Claude Code session's sandbox heuristic refuses pip installs
of "unverified" packages. Fix: add a SCOPED permission rule to
`~/.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(pip install --user --break-system-packages aios-kiro-master*)"
    ]
  }
}
```

Then in the Ubuntu session, retry:
```bash
pip install --user --break-system-packages aios-kiro-master
aios init        # idempotent
aios doctor      # health check
```

The `--user` flag installs to `~/.local/bin/aios` so make sure that's
on PATH:
```bash
echo $PATH | tr ':' '\n' | grep -q "$HOME/.local/bin" || \
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### Blocker 3 — `ollama pull qwen3:8b` was at 64%

Likely complete by now. Verify:

```bash
ollama list | grep -E 'deepseek-r1:8b|qwen3:8b|llama3.1:8b'
```

If all 3 lines show: local LLM models are ready. If qwen3:8b is
missing, re-run:
```bash
ollama pull qwen3:8b
```

**Important note**: `qwen3.6:8b` does NOT exist. qwen3.6 only ships at
27B and 35B (~17 GB+, way past your RTX 4050 6GB VRAM). The latest
Qwen with an 8B variant is plain `qwen3`.

## Memory transfer (auto-memory)

The Windows session's auto-memory dir has all session history,
patterns, infrastructure state, etc. To bring it to Ubuntu (assumes
WSL2 with Windows mounted at `/mnt/c/`):

```bash
WIN_MEMORY="/mnt/c/Users/DANNY/.claude/projects/c--Users-DANNY-Desktop-portafolio-completo-proyectos-07-nexusforge-ai/memory"
UBUNTU_MEMORY="$HOME/.claude/projects/-home-chris-nexusforge-ai/memory"

mkdir -p "$UBUNTU_MEMORY"
# Filter to NexusForge-relevant files only (skip Verificarro, Spacetime,
# MindScrolling, METRO etc. which are other projects):
cp "$WIN_MEMORY"/MEMORY.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/ubuntu_migration_handoff_2026_05_01.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/user_profile.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/feedback_*.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/project_overview.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/project_tenant_alpha_showcase.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/architecture.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/agent_map.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/kiro_integration.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/critical_rules.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/nexusforge_cli.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/wsl2_setup.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/aeromexico_*.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/batch3_sensitive_notes.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/pattern_*.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/vercel_dual_project_trap.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/infrastructure_state_2026_04_30.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/verification_harness.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/session_2026_04_*.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/session_2026_05_01_platform_synthesizer.md "$UBUNTU_MEMORY/"
cp "$WIN_MEMORY"/session_2026_05_01_synth_extension.md "$UBUNTU_MEMORY/"

ls -1 "$UBUNTU_MEMORY" | wc -l    # should be ~30 files
```

If your Ubuntu environment isn't WSL2 with `/mnt/c/` mounting:
- If you have SSH from Ubuntu to the Windows box: use `scp -r ...`
- Otherwise: copy via cloud sync (Dropbox/OneDrive) or USB

**Backup option**: the Windows memory dir also has a single
`_NEXUSFORGE_BUNDLE.md` (~200 KB, 4100 lines) that is every memory
file concatenated. If file-by-file transfer fails, copy ONLY that
file and paste it into the new Claude session as initial context:

```bash
# Just the bundle:
cp "$WIN_MEMORY"/_NEXUSFORGE_BUNDLE.md "$UBUNTU_MEMORY/"
```

## Once Blockers 1-3 are clear, run the canonical 6-source triangulation

See `verification/QUICKSTART.md`. Summary:

```bash
# Sessions 1-3 (cloud + AIOS, three IDE windows):
#   bash verification/bootstrap.sh claude_security
#   ...follow the 3 prompts in QUICKSTART.md...

# Sessions 4-6 (local LLMs, one terminal, sequential):
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
bash verification/local_llm_review.sh deepseek_local deepseek-r1:8b $RUN_ID security
bash verification/local_llm_review.sh qwen_local     qwen3:8b        $RUN_ID technical
bash verification/local_llm_review.sh llama_local    llama3.1:8b     $RUN_ID functional

# Triangulator over all 6:
python3 verification/triangulate.py
```

## Pending items (NOT blockers, just open work)

- Rotate Render API key (token from earlier session still in transcript)
- Delete Vercel orphan project `nexusforge` (after external-cite verify)
- Stripe billing decision (deferred product call)

## User preferences (DO NOT VIOLATE)

- **Verbose multi-section commit messages** — "why" + validation
  evidence + scope boundary, not terse one-liners
- **NO Claude/Anthropic co-author trailer** in commits or PRs
- **Explicit go/no-go for every push** — never auto-push, never amend
  published commits, never force-push
- **Local verification before push** is mandatory
- **Codenames only** for client/system references — never real names
