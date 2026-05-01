# Verification report — `<TOOL_ID>`

_Run id: `<RUN_ID>`_
_Generated: `<UTC_TIMESTAMP>`_
_Repo commit: `<GIT_SHA>` (`<BRANCH>`)_

## Stack snapshot

- backend: http://localhost:18000
- frontend: http://localhost:15173
- postgres: localhost:15432 (isolated from dev)
- redis: localhost:16379
- mongodb: localhost:27018
- ollama: http://localhost:11435

## Security scan

Findings raw counts, by severity:

| Severity | Count |
|---|---|
| critical | <N> |
| high | <N> |
| medium | <N> |
| low | <N> |
| info | <N> |

Top 5 findings to fix first (sorted by severity DESC, then category):

1. **[critical]** [<category>] `<file>:<line>` — <title>
2. ...

## Functionality smoke

| Surface | Status | Duration |
|---|---|---|
| operational health | ✅/❌ | Nms |
| auth | ✅/❌ | Nms |
| wizard | ✅/❌ | Nms |
| workflow runtime | ✅/❌ | Nms |
| platform synth | ✅/❌ | Nms |
| refactor engine | ✅/❌ | Nms |
| audit | ✅/❌ | Nms |

Notes (any non-default behavior, surface gaps the smoke can't reach):

- ...

## Gaps the harness can't see (analyst-added)

What this scanner / model session noticed that the automated layer
won't catch. Free-form, but please tag with `[security]` /
`[functionality]` / `[ux]` / `[performance]` / `[ops]` so the
triangulator's manual-finding parser can pick them up.

- `[security]` …
- `[functionality]` …

## Recommendations (analyst-added, prioritized)

1. ...
2. ...
3. ...

## Run metadata

```json
{
  "tool_id": "...",
  "run_id": "...",
  "started_utc": "...",
  "git_commit": "...",
  "git_branch": "...",
  "stack_endpoints": { ... }
}
```
