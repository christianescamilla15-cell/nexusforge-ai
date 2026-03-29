"""
Enterprise Operations Workflow — orchestrates 8 agents for business request processing.
Integrates with NexusForge execution tracking for full observability.
"""
import time
import uuid
from .schemas import OperationsRequest, OperationsResponse
from .agents import (
    intake_agent, intent_classifier_agent, customer_context_agent,
    document_rag_agent, scheduler_agent, crm_update_agent,
    notification_agent, supervisor_agent,
)
from app.metrics.collector import collector
from app.models.workflow_run import RunStatus


async def run_enterprise_ops_workflow(request: OperationsRequest) -> OperationsResponse:
    """Execute the full enterprise operations workflow with tracking."""
    run_id = str(uuid.uuid4())
    start_time = time.time()
    lang = request.language
    actions_taken = []
    agents_used = []

    # Start tracking
    run = collector.start_run(
        workflow_name="enterprise_operations",
        topology="sequential",
    )
    tracked_run_id = run.id

    try:
        # Step 1: Intake
        step1 = collector.start_step(tracked_run_id, "IntakeAgent", 0)
        intake_result = await intake_agent(request.model_dump(), lang)
        collector.end_step(step1)
        agents_used.append("IntakeAgent")
        actions_taken.append(f"intake: {intake_result['status']}")

        if intake_result["status"] == "error":
            collector.end_run(tracked_run_id, status=RunStatus.FAILED)
            return OperationsResponse(
                run_id=run_id, status="error", intent="unknown",
                response_message=intake_result.get("error", "Error en intake"),
                agents_used=agents_used,
            )

        # Step 2: Intent Classification
        step2 = collector.start_step(tracked_run_id, "IntentClassifierAgent", 1)
        intent_result = await intent_classifier_agent(request.message, lang)
        collector.end_step(step2)
        agents_used.append("IntentClassifierAgent")
        intent = intent_result["intent"]
        actions_taken.append(f"intent: {intent} (confidence: {intent_result['confidence']})")

        # Step 3: Customer Context
        step3 = collector.start_step(tracked_run_id, "CustomerContextAgent", 2)
        context_result = await customer_context_agent(request.customer_id, lang)
        collector.end_step(step3)
        agents_used.append("CustomerContextAgent")
        customer = context_result.get("customer")
        customer_name = customer["name"] if customer else None
        actions_taken.append(f"customer: {customer_name or 'not found'}")

        # Step 4: Document RAG
        step4 = collector.start_step(tracked_run_id, "DocumentRAGAgent", 3)
        rag_result = await document_rag_agent(intent, request.message, customer, lang)
        collector.end_step(step4)
        agents_used.append("DocumentRAGAgent")
        documents = rag_result.get("documents", [])
        actions_taken.append(f"documents: {rag_result['documents_found']} found")

        # Step 5: Scheduler (only for scheduling intents)
        if intent == "reschedule_meeting":
            step5 = collector.start_step(tracked_run_id, "SchedulerAgent", 4)
            sched_result = await scheduler_agent(customer_name, request.message, lang)
            collector.end_step(step5)
            agents_used.append("SchedulerAgent")
            actions_taken.append(f"scheduler: {sched_result['action']} ({sched_result.get('selected_slot', 'none')})")

        # Step 6: CRM Update
        step6 = collector.start_step(tracked_run_id, "CRMUpdateAgent", 5)
        crm_result = await crm_update_agent(request.customer_id, intent, actions_taken, lang)
        collector.end_step(step6)
        agents_used.append("CRMUpdateAgent")
        crm_updated = crm_result.get("crm_record_created", False)
        actions_taken.append(f"crm: {'updated' if crm_updated else 'skipped'}")

        # Step 7: Notification
        step7 = collector.start_step(tracked_run_id, "NotificationAgent", 6)
        notif_result = await notification_agent(customer_name, intent, actions_taken, lang)
        collector.end_step(step7)
        agents_used.append("NotificationAgent")
        notification_sent = notif_result.get("notification_sent", False)
        actions_taken.append(f"notification: {'sent' if notification_sent else 'failed'}")

        # Step 8: Supervisor (final response generation)
        step8 = collector.start_step(tracked_run_id, "SupervisorAgent", 7)
        supervisor_result = await supervisor_agent(intent, customer_name, actions_taken, documents, lang)
        collector.end_step(step8, provider=supervisor_result.get("provider", ""), tokens=supervisor_result.get("total_tokens", 0), cost=supervisor_result.get("cost_usd", 0.0))
        agents_used.append("SupervisorAgent")

        # Propagate LLM usage from supervisor
        total_tokens = supervisor_result.get("total_tokens", 0)
        total_cost = supervisor_result.get("cost_usd", 0.0)
        provider_used = supervisor_result.get("provider", "none")
        model_used = supervisor_result.get("model", "none")
        llm_used = supervisor_result.get("llm_used", False)

        # Complete tracking
        collector.end_run(tracked_run_id)

        processing_time = round((time.time() - start_time) * 1000, 1)

        return OperationsResponse(
            run_id=run_id,
            status="completed",
            intent=intent,
            customer_name=customer_name,
            actions_taken=actions_taken,
            response_message=supervisor_result["response_message"],
            documents_consulted=[d.get("title", "") for d in documents],
            crm_updated=crm_updated,
            notification_sent=notification_sent,
            processing_time_ms=processing_time,
            agents_used=agents_used,
            provider=provider_used,
            model=model_used,
            total_tokens=total_tokens,
            tokens_input=supervisor_result.get("tokens_input", 0),
            tokens_output=supervisor_result.get("tokens_output", 0),
            cost_usd=total_cost,
            llm_used=llm_used,
        )

    except Exception as e:
        collector.end_run(tracked_run_id, status=RunStatus.FAILED)
        return OperationsResponse(
            run_id=run_id, status="error", intent="unknown",
            response_message=f"Error processing request: {str(e)}",
            agents_used=agents_used,
            processing_time_ms=round((time.time() - start_time) * 1000, 1),
        )
