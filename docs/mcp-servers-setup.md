# MCP servers — ready-to-activate recipes

> Reference document. **Not checked in as active config.** Each section
> contains the exact snippets to add to your personal `~/.claude.json`
> once you have the required API keys. Adding a broken MCP server
> config to settings.json makes Claude Code try to connect at session
> start and log errors — better to keep this as a recipe until the key
> is ready.
>
> Scope: this is for Claude Code (the tool), not for NexusForge (the
> product). These MCPs give Claude Code the ability to interact with
> Render / GitHub / Postgres directly instead of going through curl
> and shell scripts.

## Why MCP servers matter

The Model Context Protocol lets Claude Code call external tools as if
they were native. Instead of me running `curl -X GET https://api.render.com/...`
and parsing JSON in bash, an MCP server exposes structured tools like
`render.list_services()` or `github.get_pr_comments(pr_number)` that I
can invoke directly.

For NexusForge specifically, the 3 highest-ROI MCPs are:

1. **Render** — eliminates the risk of violating the critical rule
   "NEVER use PUT on Render /env-vars without ALL existing vars". The
   Render MCP exposes safe get-merge-patch primitives.
2. **GitHub** — open/merge PRs, read review comments, check CI status
   without leaving the chat.
3. **PostgreSQL** — query NexusForge's production DB (read-only
   recommended) without writing Python scripts.

## Configuration file location

- **Personal** (recommended for API keys): `~/.claude.json` (Windows:
  `C:\Users\DANNY\.claude.json`)
- **Project-scoped, shared**: `.claude/.mcp.json` — **avoid** for
  secret-carrying MCPs. Only use if the config is keyless.

All 3 MCPs below carry secrets (API keys), so use `~/.claude.json`.

---

## 1. Render MCP server (HIGHEST PRIORITY)

### Prerequisites

1. Go to Render dashboard → Account Settings → API Keys → **Create API Key**
2. Name it something like `claude-code-nexusforge`
3. Copy the key (you only see it once)
4. Set it as an environment variable in your OS:
   - **Windows (PowerShell as admin)**:
     ```powershell
     [Environment]::SetEnvironmentVariable("RENDER_API_KEY", "rnd_xxxxxxxxxxxxx", "User")
     ```
     Then restart VS Code / Claude Code to pick up the new env var.
   - **Alternative**: put it in a `.env` file in your home dir and
     source it from your shell profile.

### Config snippet for `~/.claude.json`

```json
{
  "mcpServers": {
    "render": {
      "type": "http",
      "url": "https://mcp.render.com/mcp",
      "headers": {
        "Authorization": "Bearer ${RENDER_API_KEY}"
      },
      "allowedEnvVars": ["RENDER_API_KEY"]
    }
  }
}
```

If `~/.claude.json` already has other content, merge into the existing
`mcpServers` object rather than replacing.

### CLI alternative (if Claude Code version ≥ 2.1.x)

```bash
claude mcp add --transport http render https://mcp.render.com/mcp \
  --header "Authorization: Bearer $RENDER_API_KEY"
```

### What you unlock

Once active, I (or the `NexusForge Deployer` subagent) can:

- List services: `render.list_services()`
- Get current env vars safely: `render.get_env_vars(service_id)` — no
  risk of the PUT-overwrite trap
- Patch env vars atomically (merge, not replace)
- Tail logs: `render.tail_logs(service_id, lines=100)`
- Check deploy status: `render.get_latest_deploy(service_id)`
- Trigger manual redeploys

### Security notes

- **Read scope first**. Render's MCP supports scoping the API key to
  read-only. Start with that, grant write later only if needed.
- The key has access to your entire Render account. Treat it like a
  password. Never commit it; never share it.
- If revoked: delete the key in Render dashboard, restart Claude Code.

---

## 2. GitHub MCP server

### Prerequisites

1. GitHub → Settings → Developer settings → Personal access tokens →
   **Tokens (classic)** → Generate new token
2. Name: `claude-code-nexusforge`
3. Scopes needed:
   - `repo` (required — for PR/issue access)
   - `read:org` (optional — if you want to query org-level info)
   - `workflow` (optional — for Actions visibility)
4. Copy the token (ghp_...) — only visible once
5. Set as env var `GH_TOKEN` (same procedure as RENDER_API_KEY above)

### Config snippet for `~/.claude.json`

```json
{
  "mcpServers": {
    "github": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GH_TOKEN}"
      },
      "allowedEnvVars": ["GH_TOKEN"]
    }
  }
}
```

### What you unlock

- Open PRs: `github.create_pull_request(...)` — useful for the 2
  unmerged feature branches (anthropic-sdk-bump, context-editing)
- Read PR comments: `github.get_pull_request_comments(...)`
- Merge PRs: `github.merge_pull_request(...)`
- List Actions runs, workflows, failures
- Create / close issues
- Tag releases

### Alternative

If you already use the `gh` CLI, it is functionally equivalent for
most operations. The MCP version is better for programmatic access
from the chat loop; the CLI is better for quick manual commands.

**Recommendation for NexusForge:** use the `gh` CLI for now
(simpler, no MCP overhead). Revisit the MCP if you find yourself
asking me to do the same GitHub operations repeatedly.

---

## 3. PostgreSQL MCP server

### Prerequisites

1. Get the Postgres connection string for NexusForge's database.
   - In Render dashboard → your Postgres service → "Connect" → copy
     the **External Database URL** (starts with `postgresql://`)
   - **Important**: Use a **read-only** user if possible. In Render
     you can create additional users via the dashboard.
2. Set as env var `DATABASE_URL` (same procedure as above)

### Config snippet for `~/.claude.json`

```json
{
  "mcpServers": {
    "postgres": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "${DATABASE_URL}"
      ],
      "allowedEnvVars": ["DATABASE_URL"]
    }
  }
}
```

### What you unlock

- Query the live DB: "how many executions in the last 24h?"
- Inspect schema: `postgres.list_tables()`, `postgres.describe_table(...)`
- Read pgvector semantic memory directly
- Check migration state (the `_migrations` table)

### Security notes (critical)

- **Use a read-only role.** Never hand Claude Code write access to
  production unless you explicitly need it.
- Do NOT use a superuser connection string. Create a dedicated role:
  ```sql
  CREATE ROLE claude_readonly LOGIN PASSWORD '...';
  GRANT CONNECT ON DATABASE nexusforge TO claude_readonly;
  GRANT USAGE ON SCHEMA public TO claude_readonly;
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO claude_readonly;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO claude_readonly;
  ```
- Revoke write permissions explicitly:
  ```sql
  REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM claude_readonly;
  ```
- Log every query the MCP makes. Render Postgres has query logging
  available — enable it.

---

## 4. (Bonus) Vercel MCP — not official

As of 2026-04-10 there is **no official Anthropic / Vercel MCP server**.
The community has published some, but none are vetted. For Vercel
operations, use the `vercel` CLI directly — it is mature and
scriptable:

```bash
vercel --prod               # deploy
vercel alias ls             # list domain aliases
vercel rollback <deploy-id> # roll back to a previous deployment
```

The `NexusForge Deployer` subagent already knows these patterns.

---

## 5. Activation checklist

When you are ready to activate any of the above:

- [ ] Get the API key / token / connection string
- [ ] Set as persistent env var in your OS (not just shell session)
- [ ] Add the config snippet to `~/.claude.json` (merge into existing
      `mcpServers` if present)
- [ ] Restart Claude Code (or run `/mcp` to see if it picks up without
      restart — depends on version)
- [ ] Verify with a read-only operation first:
  - Render: list services
  - GitHub: list open PRs
  - Postgres: list tables
- [ ] If all good, tell me and I will start using it immediately

## 6. When to prefer MCP vs CLI

| Operation | Prefer MCP | Prefer CLI |
|---|---|---|
| One-shot ad-hoc command | | CLI (faster) |
| Repeated programmatic access | MCP (typed) | |
| Safe env-var merge on Render | MCP (critical rule protection) | |
| Query the DB mid-conversation | MCP | |
| Deploy frontend manually | | `vercel --prod` |
| Open a PR | `gh pr create` (simpler) | MCP (if automated) |
| Check deploy logs | MCP (structured) | `render logs` |

## 7. Session-specific notes

- **2026-04-10**: user deferred Render MCP setup because
  `RENDER_API_KEY` does not exist yet. Revisit when the key is created.
  See also `session_2026_04_11_research.md` in memory.

## 8. (Bonus) Scheduled Claude Code changelog check

Not an MCP server — a Claude Code `schedule` pattern. Documented here
because it keeps all "orchestrator iteration" recipes in one file.

### What it does

Runs a recurring remote agent that fetches the Claude Code CHANGELOG
and the `anthropic-sdk-python` CHANGELOG, compares them against the
versions currently pinned in the project, and reports anything new
that is relevant to NexusForge. The recurring cadence means you get
an automatic heads-up when a feature that matters to the 4-feature
adoption roadmap ships.

### Prerequisites

- Claude Code version that ships the `schedule` skill (check
  `/help` or run `schedule list` to verify)
- Active account on the Claude Code remote scheduler (usually tied
  to your Anthropic account)
- **Awareness**: scheduled remote agents run on Anthropic's
  infrastructure and may incur usage costs per run. Start with a
  weekly cadence (4-5 runs/month) to keep costs minimal.

### Activation

This is NOT a settings.json config. Use the `schedule` skill directly
in a Claude Code session:

```
/schedule create "weekly-claudecode-changelog-check"
  --cron "0 9 * * MON"
  --prompt "Fetch https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md and https://github.com/anthropics/anthropic-sdk-python/blob/main/CHANGELOG.md. Compare against my pinned versions in backend/requirements.txt (anthropic) and note any changes since the last run. Report: (1) new Claude Code features relevant to NexusForge adoption roadmap in docs/anthropic-features-research.md, (2) new anthropic SDK versions and their breaking changes, (3) any betas relevant to the 4-feature plan. Do NOT open PRs. Do NOT modify files. Read-only report."
```

Adjust the cron expression to your preference. `0 9 * * MON` is
"09:00 every Monday". Other useful patterns:
- `0 9 * * 1,4` — Monday and Thursday 09:00
- `0 9 1 * *` — first day of the month 09:00 (monthly)

### Reading the reports

Scheduled agent outputs land in your Claude Code inbox (or equivalent
in your version — check `/schedule list`). When you see a report, you
can paste the relevant parts into a new session to kick off the
research + adoption workflow (which is what `/nexusforge-research`
skill is for).

### Cost control

- Keep the prompt short and focused. Long prompts + deep web fetches
  burn more tokens.
- Set a reasonable `max_turns` if supported by your version.
- Disable via `/schedule delete weekly-claudecode-changelog-check`
  if you no longer want it.

### Alternative (no scheduled agent)

If you do not want to run a scheduled remote agent, you can invoke
the same research prompt manually once a month using the
`/nexusforge-research` skill from a regular session. It costs nothing
extra and only runs when you explicitly want it.

**Recommendation for NexusForge:** start with the manual monthly
invocation. Move to scheduled only if you notice you are missing
relevant features because you forgot to check.

---

## Related

- Main Claude Code docs on MCP: https://code.claude.com/docs/en/mcp
- Render MCP docs: https://render.com/docs/mcp-server
- GitHub MCP server: https://github.com/modelcontextprotocol/servers/tree/main/src/github
- Postgres MCP server: https://github.com/modelcontextprotocol/servers/tree/main/src/postgres
- Schedule skill (local reference): invoke `/schedule` in a Claude
  Code session to see its help and current scheduled agents
