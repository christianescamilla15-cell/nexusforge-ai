"""
RunLogger — Central service for workflow execution observability.

Connects workflow_runs, workflow_steps, and agent_events to provide
automatic logging of every execution phase in NexusForge AI.

Usage:
    logger = RunLogger(db)
    run_id = logger.start_workflow("research_pipeline", "swarm", {"query": "..."})
    step_id = logger.start_step(run_id, 1, "ResearchAgent")
    logger.finish_step(step_id, output_payload=result)
    logger.finish_workflow(run_id, output_payload=final_result)
"""
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models.workflow_run import WorkflowRun
from app.db.models.workflow_step import WorkflowStep
from app.db.models.agent_event import AgentEvent


class RunLogger:

    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────
    # WORKFLOW LEVEL
    # ─────────────────────────────────────────

    def start_workflow(
        self,
        workflow_name: str,
        topology: str,
        input_payload: dict | None = None,
    ):
        """Start a new workflow run and return its ID."""
        run = WorkflowRun(
            workflow_name=workflow_name,
            topology=topology,
            status="running",
            input_payload=input_payload,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        self.log_event(
            run_id=run.id,
            agent_name="system",
            event_type="workflow_started",
            message=f"Workflow '{workflow_name}' started with topology '{topology}'",
        )

        return run.id

    def finish_workflow(
        self,
        run_id,
        output_payload: dict | None = None,
        status: str = "success",
    ):
        """Mark a workflow run as finished."""
        run = self.db.get(WorkflowRun, run_id)
        if not run:
            return

        run.status = status
        run.output_payload = output_payload
        run.finished_at = datetime.utcnow()

        if run.started_at:
            latency = datetime.utcnow() - run.started_at
            run.total_latency_ms = int(latency.total_seconds() * 1000)

        self.log_event(
            run_id=run_id,
            agent_name="system",
            event_type="workflow_completed",
            message=f"Workflow completed with status '{status}' in {run.total_latency_ms}ms",
        )

        self.db.commit()

    def fail_workflow(self, run_id, error_message: str):
        """Mark a workflow run as failed."""
        run = self.db.get(WorkflowRun, run_id)
        if not run:
            return

        run.status = "failed"
        run.finished_at = datetime.utcnow()

        if run.started_at:
            latency = datetime.utcnow() - run.started_at
            run.total_latency_ms = int(latency.total_seconds() * 1000)

        self.log_event(
            run_id=run_id,
            agent_name="system",
            event_type="workflow_failed",
            message=error_message,
        )

        self.db.commit()

    # ─────────────────────────────────────────
    # STEP LEVEL
    # ─────────────────────────────────────────

    def start_step(
        self,
        run_id,
        step_order: int,
        agent_name: str,
        input_payload: dict | None = None,
    ):
        """Start a new step within a workflow run."""
        step = WorkflowStep(
            run_id=run_id,
            step_order=step_order,
            agent_name=agent_name,
            status="running",
            started_at=datetime.utcnow(),
            input_payload=input_payload,
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)

        self.log_event(
            run_id=run_id,
            step_id=step.id,
            agent_name=agent_name,
            event_type="step_started",
            message=f"Agent '{agent_name}' started (step {step_order})",
        )

        return step.id

    def finish_step(
        self,
        step_id,
        output_payload: dict | None = None,
        provider_name: str | None = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ):
        """Mark a step as successfully completed."""
        step = self.db.get(WorkflowStep, step_id)
        if not step:
            return

        step.status = "success"
        step.output_payload = output_payload
        step.finished_at = datetime.utcnow()
        step.tokens_used = tokens_used
        step.cost_usd = cost_usd

        if provider_name:
            step.provider_name = provider_name

        if step.started_at:
            latency = datetime.utcnow() - step.started_at
            step.latency_ms = int(latency.total_seconds() * 1000)

        self.log_event(
            run_id=step.run_id,
            step_id=step.id,
            agent_name=step.agent_name,
            event_type="step_completed",
            message=f"Agent '{step.agent_name}' completed in {step.latency_ms}ms",
            metadata={"provider": provider_name, "tokens": tokens_used},
        )

        # Update run-level aggregates
        run = self.db.get(WorkflowRun, step.run_id)
        if run:
            run.total_tokens = (run.total_tokens or 0) + tokens_used
            run.total_cost_usd = float(run.total_cost_usd or 0) + cost_usd

        self.db.commit()

    def fail_step(self, step_id, error_message: str):
        """Mark a step as failed."""
        step = self.db.get(WorkflowStep, step_id)
        if not step:
            return

        step.status = "failed"
        step.error_message = error_message
        step.finished_at = datetime.utcnow()

        if step.started_at:
            latency = datetime.utcnow() - step.started_at
            step.latency_ms = int(latency.total_seconds() * 1000)

        self.log_event(
            run_id=step.run_id,
            step_id=step.id,
            agent_name=step.agent_name,
            event_type="step_failed",
            message=error_message,
        )

        self.db.commit()

    # ─────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────

    def log_event(
        self,
        run_id,
        agent_name: str,
        event_type: str,
        step_id=None,
        message: str | None = None,
        metadata: dict | None = None,
    ):
        """Log a generic event for observability."""
        event = AgentEvent(
            run_id=run_id,
            step_id=step_id,
            agent_name=agent_name,
            event_type=event_type,
            event_message=message,
            metadata=metadata,
        )
        self.db.add(event)
        self.db.commit()

    # ─────────────────────────────────────────
    # RETRIES
    # ─────────────────────────────────────────

    def log_retry(self, step_id, attempt: int = 0):
        """Record a retry attempt for a step."""
        step = self.db.get(WorkflowStep, step_id)
        if not step:
            return

        step.retry_count += 1
        self.db.commit()

        # Update run-level retry count
        run = self.db.get(WorkflowRun, step.run_id)
        if run:
            run.retry_count = (run.retry_count or 0) + 1
            self.db.commit()

        self.log_event(
            run_id=step.run_id,
            step_id=step.id,
            agent_name=step.agent_name,
            event_type="retry",
            message=f"Agent '{step.agent_name}' retry attempt {attempt}",
            metadata={"attempt": attempt},
        )

    # ─────────────────────────────────────────
    # FALLBACK
    # ─────────────────────────────────────────

    def log_fallback(self, step_id, from_provider: str, to_provider: str):
        """Record a provider fallback for a step."""
        step = self.db.get(WorkflowStep, step_id)
        if not step:
            return

        step.fallback_triggered = True
        step.provider_name = to_provider

        run = self.db.get(WorkflowRun, step.run_id)
        if run:
            run.fallback_used = True

        self.db.commit()

        self.log_event(
            run_id=step.run_id,
            step_id=step.id,
            agent_name=step.agent_name,
            event_type="fallback_triggered",
            message=f"Fallback: {from_provider} -> {to_provider}",
            metadata={"from": from_provider, "to": to_provider},
        )
