# Requirements: Unify Execution Tracking

## Problem
NexusForge has two execution tables (pipeline_runs and workflow_runs) causing Dashboard KPIs to show 0 despite 50+ real executions. Each execution must reflect across 7-9 pages consistently.

## Requirements

1. All execution sources (swarms, enterprise_ops, document_intelligence, analyze, drive_pipeline, portfolio_copilot) must write to workflow_runs table ONLY, not pipeline_runs
2. Dashboard KPIs must read from a single table (workflow_runs) and show real totals
3. Dashboard "Ejecuciones Recientes" must be paginated (10/page), scrollable (max 400px), with a "Clear All" button
4. The "Ejecutar" button in automation dashboards must NOT navigate away from the page — results appear inline
5. "Prueba la IA ahora" → "Crear automatización" must pre-load the analysis into the AI Wizard (type, name, description, input, output all pre-filled)
6. AI Wizard must pre-fill name and description when a type is selected (not just input/output)
7. Métricas de Costo tab must show real tokens, cost, retries and fallbacks from step_executions
8. Each swarm execution must appear in: Dashboard KPIs, Ejecuciones list, Métricas tab, Agent Activity, Status page
9. Each automation execution must appear in: its own dashboard stats, Dashboard KPIs, Ejecuciones, Métricas, Agent Activity, NotificationBell, Plan Usage
