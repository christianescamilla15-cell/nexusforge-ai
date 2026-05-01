# Quickstart — paste-and-go prompts

One prompt per session. Open a fresh agent/IDE window for each, paste
the corresponding block, let it run end-to-end. After all three
finish, run the triangulator (last section).

---

## Session 1 — Claude security review

Open Claude Code (or fresh Claude session) in the repo root and paste:

````
Sos el nodo "Claude Security Review" de una triangulación de NexusForge AI
con 3 fuentes (vos + GPT-5.5 vía Codex + AIOS). Cada nodo levanta su propio
stack aislado, corre la misma batería automatizada, y escribe un reporte
markdown con findings manuales que el harness no puede ver. El triangulator
después cruza los 3 y ranquea por agreement.

CORRER (copy-paste, capturando el run_id que imprime el step 1):
  bash verification/bootstrap.sh claude_security
  # ↑ imprime el run_id (timestamp UTC). Usalo en los siguientes:
  bash verification/security_scan.sh claude_security <run_id>
  bash verification/functionality_smoke.sh claude_security <run_id>

DESPUÉS:
  Leé los JSON generados:
    verification/reports/claude_security/<run_id>/security_findings.json
    verification/reports/claude_security/<run_id>/functionality_findings.json
    verification/reports/claude_security/<run_id>/run_metadata.json

  Escribí verification/reports/claude_security/<run_id>/report.md siguiendo
  verification/templates/report.template.md. Tu valor agregado son los
  findings MANUALES que el harness no atrapa. Foco para esta sesión:
    - Authorization edge cases (multi-tenant boundary, X-Mythos-Key derivation,
      admin-only routes con info-leak guard)
    - Crypto agility (Fernet rotation overlap MultiFernet, JWT signing alg
      pinning, refresh token rotation single-use)
    - Prompt injection en cualquier input que llegue a LLMs (chat, wizard,
      synthesizer chat, agent system prompts, memory injection)
    - Session/refresh token handling (revocation, expiry, replay)
    - Race conditions en workflow execution + self-healing strategies
    - Information leakage via error responses + stacktraces
  Cada manual finding tag con [security] / [functionality] / [ux] / [performance] / [ops].

CONSTRAINTS:
- Usá SOLO .env.verify (el bootstrap lo genera con secrets test). NUNCA tocar
  el .env de producción.
- Cero git push, cero cambios a render.yaml o config de prod.
- El stack corre en puertos aislados: backend 18000, frontend 15173 (NO en
  los de dev 8000/5173).
- NO bajes el stack al final — las otras 2 sesiones lo necesitan vivo o
  levantan el suyo (depende del modo elegido).
- Si algo falla en bootstrap, el README de verification/ tiene tabla de
  failure modes — consultala antes de improvisar.

Al terminar imprimí 1 línea:
  "claude_security run <run_id>: <N> automated + <M> manual findings"
````

---

## Session 2 — GPT-5.5 vía Codex CLI

Lanzá `codex` en el repo root y paste:

````
You are the "GPT-5.5" node of a 3-source NexusForge AI triangulation
(you + Claude Security Review + AIOS plugin). Each node runs an
isolated stack, executes the same automated battery, and writes a
markdown report with manual findings the harness cannot see. The
triangulator cross-references all three and ranks by agreement.

RUN (copy-paste, capture the run_id printed by step 1):
  bash verification/bootstrap.sh gpt55
  # ↑ prints the run_id. Use it in the next 2:
  bash verification/security_scan.sh gpt55 <run_id>
  bash verification/functionality_smoke.sh gpt55 <run_id>

THEN:
  Read the generated JSONs:
    verification/reports/gpt55/<run_id>/security_findings.json
    verification/reports/gpt55/<run_id>/functionality_findings.json
    verification/reports/gpt55/<run_id>/run_metadata.json

  Write verification/reports/gpt55/<run_id>/report.md following
  verification/templates/report.template.md. Your added value is the
  MANUAL findings the harness cannot catch. This session's focus:
    - End-to-end correctness across the platform-synth chat → templates
      → build flow (does the generated project actually run?)
    - Refactor engine: do the C# fixes actually parse + retain semantics?
      Are batches transactional?
    - Multi-agent orchestration: are the 24-agent fallback chains sound
      under provider outages? Self-healing strategy ordering?
    - Performance smells: N+1 queries, unnecessary roundtrips, missing
      indexes, sync-in-async patterns
    - Documentation accuracy: do API endpoints in CLAUDE.md still match
      app/main.py's include_router calls?
    - Type-safety + Pydantic v2 contract enforcement at boundaries
  Tag each manual finding with [security] / [functionality] / [ux] /
  [performance] / [ops].

CONSTRAINTS:
- Use only .env.verify (NEVER the prod .env)
- Zero git push, zero prod config changes
- Stack runs on isolated ports: backend 18000, frontend 15173 (NOT dev
  defaults 8000/5173)
- Don't tear down the stack at the end
- If bootstrap fails, see verification/README.md failure-modes table
  before improvising

When done print 1 line:
  "gpt55 run <run_id>: <N> automated + <M> manual findings"
````

---

## Session 3 — AIOS plugin

Open a Claude Code session with AIOS MCP wired (see
`verification/mcp/aios.example.json`) and paste:

````
Sos el nodo "AIOS" de una triangulación NexusForge AI de 3 fuentes
(vos + Claude Security Review + GPT-5.5). Tu ventaja única sobre los
otros 2 nodos: tenés acceso a la memoria persistente de AIOS via MCP,
así que podés cruzar findings con decisiones históricas, sesiones
previas, y steering docs.

CORRER (copy-paste, capturando el run_id del step 1):
  bash verification/bootstrap.sh aios
  # ↑ imprime el run_id. Usalo en los siguientes:
  bash verification/security_scan.sh aios <run_id>
  bash verification/functionality_smoke.sh aios <run_id>

DESPUÉS:
  Leé los JSON generados:
    verification/reports/aios/<run_id>/security_findings.json
    verification/reports/aios/<run_id>/functionality_findings.json
    verification/reports/aios/<run_id>/run_metadata.json

  Para CADA finding automático con severidad ≥ medium:
    Usá las MCP tools de AIOS para cruzar contra memoria:
      - aios.memory_query "<finding title o file>"
      - aios.steering_for "<file path>"
      - aios.diff_against_memory "<finding>"
    Si AIOS reconoce el finding como ya documentado/resuelto/aceptado,
    anotalo en el report como "ya conocido — ver <memory_ref>".

  Escribí verification/reports/aios/<run_id>/report.md siguiendo
  verification/templates/report.template.md. Tu foco único:
    - Spec drift: ¿qué archivos cambiaron sin actualizar steering /
      CLAUDE.md / memory?
    - Findings que ya están resueltos en memoria pero el harness vuelve
      a flaggear (false-positive validados históricamente)
    - Findings nuevos que CONTRADICEN una decisión previa documentada
      (esto es high-signal — algo regresó)
    - Cross-session patterns: ¿hay 3+ sesiones distintas reportando el
      mismo gap a lo largo del tiempo?
    - Roadmap risks visibles desde memory pero no desde el código actual
  Tag cada manual finding con [security] / [functionality] / [ux] /
  [performance] / [ops] / [drift] / [historical].

CONSTRAINTS:
- Usá SOLO .env.verify (el bootstrap lo genera). NUNCA el .env de prod.
- Cero git push, cero cambios a config de prod.
- Stack en puertos aislados: backend 18000, frontend 15173.
- NO bajes el stack al final.
- Si AIOS MCP no conecta, verificá la invocation en
  verification/mcp/aios.example.json — quizás necesite ajuste para tu
  versión.

Al terminar imprimí 1 línea:
  "aios run <run_id>: <N> automated + <M> manual findings + <K> historical-cross-refs"
````

---

## Después de las 3 sesiones — triangulación

En cualquier sesión (o terminal limpio):

```bash
python3 verification/triangulate.py
# → verification/reports/_triangulation/<ts>/triangulation.{json,md}
```

Lee el `triangulation.md`. Triage en este orden:

1. **3/3 HIGH-CONFIDENCE** — los 3 nodos lo flagearon. Esencialmente cierto. Fix primero.
2. **2/3 likely real** — 2 fuentes coinciden. Alta probabilidad. Investigar.
3. **1/3 investigate** — solo 1 fuente. Candidato a false positive, pero leelo: a veces el único que vio el bug es el que tenía el contexto correcto (ej. AIOS cruzando memoria histórica).

## Cleanup post-triangulación

```bash
docker compose -f docker-compose.verify.yml -p nexusforge_verify down -v
docker volume prune --filter label=verify-only --force
rm -rf /tmp/nexusforge_verify_synth
```

## Modo "shared stack" (3 sesiones contra UN stack)

Por default cada sesión bootstrapeala su propio stack (más limpio).
Si querés ahorrar tiempo y espacio en disco, levantá UNA vez:

```bash
bash verification/bootstrap.sh claude_security    # bootstrap único
```

Después en sesiones 2 y 3, en vez de bootstrap, hacé manualmente:

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p verification/reports/<tool_id>/$RUN_ID
cp verification/reports/claude_security/<otro_run>/run_metadata.json \
   verification/reports/<tool_id>/$RUN_ID/run_metadata.json
# y proseguí con security_scan + functionality_smoke
```

Caveat: el smoke harness crea usuarios test con email único (uuid),
así que las 3 sesiones podrían registrarse en paralelo sin colisión.
Pero los workflow-id se acumulan en la misma DB; si ves 3× los mismos
workflows en la audit table, sabés por qué.
