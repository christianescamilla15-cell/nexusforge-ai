# Quickstart — paste-and-go prompts

The canonical triangulation pass uses **6 sources**:

  1. `claude_security` — Claude security review (cloud)
  2. `gpt55` — GPT-5.5 via Codex (cloud)
  3. `aios` — AIOS persistent-memory cross-ref (local CLI)
  4. `deepseek_local` — DeepSeek-R1 8B (Ollama, security focus)
  5. `qwen_local` — Qwen 3.6 8B (Ollama, technical focus)
  6. `llama_local` — Llama 3.1 8B (Ollama, functional focus)

All 6 are **mandatory for a full pass**. Skipping a node degrades the
triangulator's agreement scoring (3-source clusters become 2-source,
etc.). Run subsets only when you knowingly want a partial pass.

## Pre-requisitos (una sola vez por máquina)

```bash
# 1. Repo en sync
cd /home/chris/nexusforge-ai
git pull origin master

# 2. AIOS CLI (público en PyPI)
pip install aios-kiro-master
aios init        # idempotent — crea ai-system/, ai-memory/, specs/
aios doctor      # health check

# 3. Modelos locales — descargar el upgrade de Qwen (último que cabe en 6GB VRAM)
ollama pull qwen3:8b      # ~5 GB, ÚLTIMA generación Qwen con variante 8B
                          # NOTA: qwen3.6 solo tiene 27B/35B → no cabe en RTX 4050
ollama list | grep -E 'deepseek-r1:8b|qwen3:8b|llama3.1:8b'
```

Después abre 3 IDE windows distintas para Sesiones 1-3 (cloud + AIOS,
una por motor de LLM), y los nodos locales corren secuencial en una
4ta terminal.

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

## Session 3 — AIOS (CLI shell-out, no MCP)

AIOS (`aios-kiro-master`) is **not** an MCP server — it is a CLI tool.
The session calls `aios <subcommand>` via shell. Before running this
session, in your Ubuntu:

```bash
pip install aios-kiro-master      # public PyPI, free download
cd /home/chris/nexusforge-ai
aios init                          # idempotent
aios doctor                        # health check
```

Then open a Claude Code (or other agent) session in the repo and paste:

````
Sos el nodo "AIOS" de una triangulación NexusForge AI de 3 fuentes
(vos + Claude Security Review + GPT-5.5). Tu ventaja única sobre los
otros 2 nodos: AIOS tiene memoria persistente entre sesiones, así que
podés cruzar findings nuevos contra decisiones, fixes y notas
históricas que los otros nodos no ven.

AIOS es UNA CLI, NO un MCP server. Invocala via la shell tool. Si
`aios --help` falla, pará y avisá — el setup está incompleto.

CORRER (copy-paste, capturando el run_id del step 1):
  bash verification/bootstrap.sh aios
  bash verification/security_scan.sh aios <run_id>
  bash verification/functionality_smoke.sh aios <run_id>

DESPUÉS, cross-ref con memoria AIOS:
  RUN_DIR=verification/reports/aios/<run_id>
  jq -r '.findings[] | select(.severity == "high" or .severity == "critical") | .title' \
      $RUN_DIR/security_findings.json \
      | while read -r f; do
          echo "=== $f ==="
          aios memory search "$f"
          echo
        done > $RUN_DIR/memory_crossref.txt

  También útil:
    aios analyze          # arch summary del repo actual
    aios refine           # specs completeness
    aios diff             # qué cambió desde la última sesión
    aios impact           # dependency graph

ESCRIBÍ $RUN_DIR/report.md (siguiendo verification/templates/report.template.md).
Para CADA finding automático ≥ medium, marcalo en una de estas categorías
basándote en lo que dijo memory_crossref.txt:
  - "ya resuelto" — citá memory entry / commit
  - "false positive conocido" — citá entry
  - "risk documentado" — citá entry
  - "genuinamente nuevo" — sin coincidencia en memoria

Foco MANUAL único de este nodo:
  - Spec drift: archivos cambiados sin actualizar steering / CLAUDE.md / memory
  - Findings que el harness re-flaggea pero ya están resueltos en memoria
  - Findings nuevos que CONTRADICEN una decisión documentada (high-signal: regresión)
  - Cross-session patterns: 3+ sesiones reportando el mismo gap en el tiempo
  - Roadmap risks visibles desde memory pero invisibles desde el código actual
Tag manuales: [security] / [functionality] / [ux] / [performance] / [ops] / [drift] / [historical]

CONSTRAINTS:
- Solo .env.verify, NUNCA el .env de prod
- Cero git push, cero cambios a config de prod
- Stack en puertos aislados: backend 18000, frontend 15173
- NO bajes el stack al final
- Si `aios` no está instalado, parar y avisar (no inventar findings)

Al terminar imprimí 1 línea:
  "aios run <run_id>: <N> automated + <M> manual + <K> historical-cross-refs"
````

---

---

## Sesión 4-6 — nodos LOCALES (Ollama, secuenciales)

Estos 3 nodos corren contra **Ollama nativo en tu host** (puerto 11434),
NO contra el container del verify stack. Son secuenciales porque
RTX 4050 6GB solo aguanta 1 modelo a la vez en GPU.

Pre-requisito (una sola vez):

```bash
# 2 ya los tienes; descarga el upgrade del coder:
ollama pull qwen3:8b      # ~5 GB
ollama list | grep -E 'deepseek-r1:8b|qwen3:8b|llama3.1:8b'
```

Luego, **después de que claude_security y gpt55 generaron `<run_id>`**,
los nodos locales reusan ese mismo `<run_id>` (o pasan uno nuevo
generado con `date -u +%Y%m%dT%H%M%SZ`):

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)

# Nodo 4 — DeepSeek R1 8B sobre security findings (~30s/finding)
bash verification/local_llm_review.sh deepseek_local deepseek-r1:8b $RUN_ID security

# Nodo 5 — Qwen 3.6 8B sobre tech/code findings (~30s/finding)
bash verification/local_llm_review.sh qwen_local qwen3:8b $RUN_ID technical

# Nodo 6 — Llama 3.1 8B sobre functionality (~30s/finding)
bash verification/local_llm_review.sh llama_local llama3.1:8b $RUN_ID functional
```

Los scripts:
- Reutilizan `security_findings.json` y `functionality_findings.json`
  generados por la harness en sesiones previas
- Si el tool_id no tiene su propio bootstrap, **fallback automático**
  al run más reciente de cualquier otro tool
- Llaman a Ollama con `format: "json"` para output parseable
- Escriben `manual_findings_<focus>.json` + `local_review_<focus>.md`
  en el mismo schema que los nodos cloud

Tiempo estimado: 30-50 min los 3 juntos sobre ~30 findings cada uno.

## Después de las 6 sesiones — triangulación

En cualquier sesión (o terminal limpio):

```bash
python3 verification/triangulate.py
# Sin --tools usa el default canónico (los 6: claude_security, gpt55,
# aios, deepseek_local, qwen_local, llama_local). Pasa --tools para
# correr un subset.
# → verification/reports/_triangulation/<ts>/triangulation.{json,md}
```

Lee el `triangulation.md`. Triage en este orden:

1. **6/6 HIGH-CONFIDENCE** — todos los nodos lo flagearon. Casi certeza. Fix primero.
2. **4-5/6 likely real** — mayoría coincide. Alta probabilidad. Investigar.
3. **2-3/6 mixed** — diferentes familias dijeron cosas distintas. Lee descripciones por nodo, decide.
4. **1/6 investigate** — solo 1 fuente. Candidato a false positive, pero leelo: a veces el único que vio el bug es el que tenía el contexto correcto (ej. AIOS cruzando memoria histórica, o DeepSeek razonando sobre exploitability que los otros 5 no notaron).

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
