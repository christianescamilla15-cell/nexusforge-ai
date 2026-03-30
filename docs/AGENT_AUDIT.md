# NexusForge Agent Audit Report

**Date:** 2026-03-30
**Auditor:** Automated deep audit
**Scope:** All 22 UI-listed agents + 21 backend platform agents + 21 use-case agents

---

## 1. Executive Summary

NexusForge presents **22 agents** in the frontend UI (`AgentListPage.jsx`), but these are **hardcoded demo data** (`DEMO_AGENTS`) that do NOT correspond 1:1 to the real backend agents. The system actually contains **three distinct agent layers**:

| Layer | Count | Where | Status |
|---|---|---|---|
| **Frontend UI agents** | 22 | `AgentListPage.jsx` DEMO_AGENTS array | Hardcoded demo data, not fetched from API |
| **Platform agents** (backend) | 21 | `backend/app/agents/*.py` | All implemented, registered in registry, used by engine/swarm |
| **Use-case agents** (backend) | 21 | `backend/app/use_cases/*/agents.py` | All implemented, called by workflows |

The frontend 22 agents are a **showcase/demo layer** — they display realistic-looking stats and configs but are not connected to the real backend agent registry. The backend has a real `/api/agents/` endpoint that returns the actual 21 registered platform agents, but the frontend does not call it.

---

## 2. Agent Matrix

### 2.1 Frontend UI Agents (22 — all hardcoded demo data)

| # | UI Name | Type | Has Backend Match? | Classification |
|---|---|---|---|---|
| 1 | DocClassifier | classifier | Yes — `ClassifierAgent` | **Demo + Real match** |
| 2 | EntityExtractor | extractor | Yes — `ExtractorAgent` | **Demo + Real match** |
| 3 | SummaryAgent | summarizer | Yes — `SummarizerAgent` | **Demo + Real match** |
| 4 | ContentGen | generator | No direct match | **UI-only** |
| 5 | FlowRouter | router | Yes — `RouterAgent` | **Demo + Real match** |
| 6 | DataValidator | validator | Yes — `ValidatorAgent` | **Demo + Real match** |
| 7 | SentimentAnalyzer | analyzer | Partial — `SentimentAgent` + `AnalyzerAgent` | **Demo + Partial match** |
| 8 | TranslationAgent | translator | Yes — `TranslatorAgent` | **Demo + Real match** |
| 9 | CodeReviewer | reviewer | No backend implementation | **UI-only** |
| 10 | TestGenerator | generator | No backend implementation | **UI-only** |
| 11 | APIMapper | mapper | No backend implementation | **UI-only** |
| 12 | SchemaValidator | validator | Overlaps with `ValidatorAgent` | **UI-only / Redundant** |
| 13 | DataTransformer | transformer | Partial — `NormalizerAgent` covers some | **UI-only / Partial** |
| 14 | ReportBuilder | generator | Yes — `ReporterAgent` | **Demo + Real match** |
| 15 | AlertMonitor | monitor | Yes — `MonitorAgent` | **Demo + Real match** |
| 16 | ComplianceChecker | checker | Yes — `ComplianceAgent` | **Demo + Real match** |
| 17 | PriorityRanker | ranker | No backend implementation | **UI-only** |
| 18 | DuplicateDetector | detector | No backend implementation | **UI-only** |
| 19 | ContextLinker | linker | Partial — `KnowledgeAgent` covers RAG linking | **UI-only / Partial** |
| 20 | AnomalyDetector | detector | Partial — `MonitorAgent` detects anomalies | **UI-only / Redundant** |
| 21 | FeedbackCollector | collector | No backend implementation | **UI-only** |
| 22 | QualityAssurer | assurer | Partial — `CriticAgent` + `ValidatorAgent` | **UI-only / Redundant** |

### 2.2 Backend Platform Agents (21 — all registered and implemented)

| # | Agent Type | Class | Used By Engine/Swarm? | Used By Workflow? |
|---|---|---|---|---|
| 1 | classifier | ClassifierAgent | Yes (step_runner, adaptive swarm) | No (use-case has own classifier) |
| 2 | extractor | ExtractorAgent | Yes (step_runner) | No |
| 3 | summarizer | SummarizerAgent | Yes (step_runner) | No |
| 4 | analyzer | AnalyzerAgent | Yes (step_runner) | No |
| 5 | enricher | EnricherAgent | Yes (step_runner) | No |
| 6 | validator | ValidatorAgent | Yes (step_runner) | No |
| 7 | reporter | ReporterAgent | Yes (step_runner) | No |
| 8 | repair | RepairAgent | Yes (self-healer) | No |
| 9 | normalizer | NormalizerAgent | Yes (step_runner) | No |
| 10 | researcher | ResearcherAgent | Yes (step_runner) | No |
| 11 | translator | TranslatorAgent | Yes (step_runner) | No |
| 12 | compliance | ComplianceAgent | Yes (step_runner) | No |
| 13 | monitor | MonitorAgent | Yes (step_runner) | No |
| 14 | router_agent | RouterAgent | Yes (adaptive swarm) | No |
| 15 | critic | CriticAgent | Yes (step_runner) | No |
| 16 | planner | PlannerAgent | Yes (step_runner) | No |
| 17 | knowledge | KnowledgeAgent | Yes (step_runner) | No |
| 18 | scraper | ScraperAgent | Yes (step_runner) | No |
| 19 | ocr | OCRAgent | Yes (step_runner) | No |
| 20 | sentiment | SentimentAgent | Yes (step_runner) | No |
| 21 | scheduler | SchedulerAgent | Yes (step_runner) | No |
| -- | webhook | WebhookAgent | Yes (step_runner) | No |

> Note: All 21 platform agents are available via `get_agent()` and can be invoked by the generic `step_runner.run_step()` and adaptive swarm. They are the building blocks for custom workflows created through the workflow engine.

### 2.3 Use-Case Agents (21 total across 3 workflows)

**Document Intelligence (7 agents):**
- DocumentIngestionAgent, DocumentClassifierAgent, SchemaExtractionAgent, ValidationAgent, SummaryAgent, StorageAgent, SupervisorAgent

**Enterprise Operations (8 agents):**
- IntakeAgent, IntentClassifierAgent, CustomerContextAgent, DocumentRAGAgent, SchedulerAgent, CRMUpdateAgent, NotificationAgent, SupervisorAgent

**Portfolio Copilot (6 agents):**
- RouterAgent, PortfolioRAGAgent, ProjectComparisonAgent, SkillsMapperAgent, ResponseFormatterAgent, SupervisorAgent

> These are standalone async functions (not BaseAgent subclasses) that are directly called by their respective workflow orchestrators. They are **not registered in the platform agent registry**.

---

## 3. Core vs Optional Agents

### Core (required for system operation)
- **RouterAgent** — used by adaptive swarm for topology selection
- **RepairAgent** — used by self-healing system for failed step recovery
- **ValidatorAgent** — quality gate in step pipelines
- **CriticAgent** — output quality evaluation
- **PlannerAgent** — task decomposition for complex workflows

### Supporting (extend capabilities)
- ClassifierAgent, ExtractorAgent, SummarizerAgent, AnalyzerAgent, EnricherAgent, ReporterAgent, NormalizerAgent, TranslatorAgent, ComplianceAgent, MonitorAgent, KnowledgeAgent

### Peripheral (niche or simulated)
- **ScraperAgent** — simulated web scraping (no real HTTP)
- **OCRAgent** — simulated OCR (LLM generates fake extracted text)
- **WebhookAgent** — simulated external calls (no real HTTP)
- **SchedulerAgent** — suggests scheduling but does not execute
- **SentimentAgent** — overlaps with AnalyzerAgent sentiment capabilities
- **ResearcherAgent** — simulated research (no real web search)

---

## 4. Redundancy Analysis

| Overlap | Agents Involved | Severity |
|---|---|---|
| Sentiment analysis | `SentimentAgent` vs `AnalyzerAgent` (both do sentiment) | Medium — AnalyzerAgent includes sentiment in its prompt |
| Validation/QA | `ValidatorAgent` vs `CriticAgent` (both evaluate output quality) | Low — Critic focuses on scoring, Validator on pass/fail |
| Routing | Platform `RouterAgent` vs use-case `router_agent` functions | None — different layers, different purposes |
| Scheduling | Platform `SchedulerAgent` vs use-case `scheduler_agent` | None — platform one suggests schedules, use-case one books meetings |

**Verdict:** Minor overlap between SentimentAgent and AnalyzerAgent. All other agents have sufficiently distinct roles. No agents should be removed; the SentimentAgent could be merged into AnalyzerAgent in a future refactor.

---

## 5. Customization UI Verdict

### Current State
- The `AgentDetailPanel.jsx` is a **read-only** info panel — it shows name, type, status, description, tools, system prompt, config, and stats.
- There are **no edit buttons, save buttons, or form inputs** — the panel was already read-only.
- There is **no "customize" button** anywhere in the agent UI. Clicking an agent card opens the detail panel; clicking the X closes it.
- The frontend agent list (`DEMO_AGENTS`) is hardcoded and never fetched from the backend API.

### Changes Made
- Added an informational notice at the bottom of `AgentDetailPanel.jsx`: "Agent configuration coming soon / Configuracion de agentes proximamente" to set expectations.
- No broken functionality was found to fix — the panel works correctly as a read-only display.

### Recommendation
- Connect the frontend to the real `GET /api/agents/` backend endpoint instead of using `DEMO_AGENTS`.
- Add actual configuration capabilities when the feature is ready.

---

## 6. Recommendations

### High Priority
1. **Connect frontend to real API** — Replace `DEMO_AGENTS` with a fetch to `GET /api/agents/` so the UI reflects actual registered agents (21 platform agents, not 22 fabricated ones).
2. **Add use-case agents to the UI** — The 21 use-case agents (across 3 workflows) are invisible in the agent list. Consider exposing them as a separate "Workflow Agents" section.
3. **Update AGENT_METADATA in routes** — The backend `routes/agents.py` only has metadata for 8 of the 21 registered agents. The remaining 13 return empty descriptions.

### Medium Priority
4. **Consider merging SentimentAgent into AnalyzerAgent** — Both perform sentiment analysis; the AnalyzerAgent already includes sentiment in its prompt.
5. **Mark simulated agents clearly** — ScraperAgent, OCRAgent, and WebhookAgent are simulated. The UI should indicate this.
6. **Add real stats tracking** — The frontend shows fake stats (e.g., "1,247 runs"). Connect to the real metrics collector to show actual execution data.

### Low Priority
7. **Standardize agent architecture** — Use-case agents are plain async functions while platform agents inherit from `BaseAgent`. Consider making use-case agents also use the `BaseAgent` class for consistency.
8. **Remove or implement UI-only agents** — 7 of the 22 UI agents (CodeReviewer, TestGenerator, APIMapper, PriorityRanker, DuplicateDetector, FeedbackCollector, and ContentGen) have no backend counterpart at all. Either implement them or remove them from the demo list.

---

## Appendix: File Locations

| Component | Path |
|---|---|
| Frontend agent list | `frontend/src/features/agents/AgentListPage.jsx` |
| Frontend agent detail | `frontend/src/features/agents/AgentDetailPanel.jsx` |
| Frontend agent card | `frontend/src/features/agents/AgentCard.jsx` |
| Backend platform agents | `backend/app/agents/*.py` |
| Agent registry | `backend/app/agents/registry.py` |
| Agent base class | `backend/app/agents/base.py` |
| Agent API routes | `backend/app/routes/agents.py` |
| Step runner (uses agents) | `backend/app/engine/step_runner.py` |
| Adaptive swarm (uses router) | `backend/app/swarms/adaptive.py` |
| Self-healer (uses repair) | `backend/app/healing/strategies.py` |
| Doc Intelligence agents | `backend/app/use_cases/document_intelligence/agents.py` |
| Enterprise Ops agents | `backend/app/use_cases/enterprise_ops/agents.py` |
| Portfolio Copilot agents | `backend/app/use_cases/portfolio_copilot/agents.py` |
