# AIOS connector — CLI shell-out (NOT MCP)

This file used to be `aios.example.json` with an MCP server config.
**That was wrong.** AIOS (`aios-kiro-master`) is **not** itself an MCP
server — it is a CLI tool that, among other things, *configures* MCP
servers for Kiro IDE. So you do not register AIOS in
`~/.claude/settings.json` mcpServers; you invoke `aios <subcommand>`
from the shell.

## Install

Public on PyPI:

```bash
pip install aios-kiro-master
```

(Package name has hyphens; the import name is `aios_kiro_master`; the
binary is just `aios`.)

## Initialize in the repo (once per repo)

```bash
cd /home/chris/nexusforge-ai
aios init        # creates ai-system/, ai-memory/, specs/ if absent
aios doctor      # health check; reports any missing pieces
```

If `aios init` says it already exists, that is fine — it is idempotent.

## Subcommands the AIOS triangulation node uses

| Goal | Command |
|---|---|
| Cross-ref a finding against persistent memory | `aios memory search "<finding title or file>"` |
| Memory stats / size | `aios memory` |
| Repo architecture summary | `aios analyze` |
| Find code by pattern | `aios search "<pattern>"` |
| Are specs complete? | `aios refine` |
| Dependency graph + impact analysis | `aios impact` |
| Incremental changes since last session | `aios diff` |
| Auto-generate steering docs | `aios steer` |
| Changelog | `aios changelog` |

Full list: `aios --help`.

## Why a "memory cross-ref" matters for triangulation

The AIOS node's unique value vs. Claude Security and GPT-5.5 nodes is
its **persistent memory across sessions**. A finding that is "new
according to a stateless LLM" can be "already triaged in memory N
weeks ago" — that is high-signal output the other two nodes cannot
produce.

Recommended flow inside the AIOS triangulation session:

```bash
# After the harness writes security_findings.json, cross-ref each
# high/critical finding against AIOS memory:
jq -r '.findings[] | select(.severity == "high" or .severity == "critical") | .title' \
    verification/reports/aios/<run_id>/security_findings.json \
    | while read -r finding; do
        echo "=== $finding ==="
        aios memory search "$finding"
        echo
      done > verification/reports/aios/<run_id>/memory_crossref.txt
```

Then in `report.md`, for each automated finding, note whether AIOS
memory recognized it as:

- **Already resolved**: cite the memory entry / commit
- **Already accepted as known false positive**: cite the entry
- **Already documented as risk**: cite the entry
- **Genuinely new**: leave a note that this did not ring a bell

## Caveats

- AIOS Master is licensed Proprietary. The PyPI package is public,
  but commercial use has terms — read the LICENSE before redistribution.
- `aios voice` requires extras: `pip install "aios-kiro-master[voice]"`
- The `aios mcp` subcommand writes `.kiro/settings/mcp.json` for the
  Kiro IDE. It is NOT the entry point for using AIOS from a Claude
  Code or Codex session — those sessions invoke `aios <subcommand>`
  via the shell tool.
