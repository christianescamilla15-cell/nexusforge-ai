"""Document Intelligence Workflow — orchestrates 7 agents for document processing with tracking."""
import time
import uuid
from .schemas import DocumentIntelligenceInput, DocumentIntelligenceFinalOutput
from .agents import (
    document_ingestion_agent, document_classifier_agent, schema_extraction_agent,
    validation_agent, summary_agent, storage_agent, supervisor_agent,
)
from app.metrics.collector import collector


async def run_document_intelligence_workflow(request: DocumentIntelligenceInput) -> DocumentIntelligenceFinalOutput:
    run_id = str(uuid.uuid4())
    start_time = time.time()
    lang = request.language
    actions = []
    agents_used = []

    run = collector.start_run(workflow_name="document_intelligence", topology="sequential")
    tracked_id = run.id

    try:
        # Step 1: Ingestion
        s1 = collector.start_step(tracked_id, "DocumentIngestionAgent", 0)
        ingest = await document_ingestion_agent(request.content, request.filename, lang)
        collector.end_step(s1)
        agents_used.append("DocumentIngestionAgent")
        actions.append(f"ingestion: {ingest['word_count']} words, {ingest['char_count']} chars")

        if ingest["status"] == "error":
            collector.end_run(tracked_id, status="failed")
            return DocumentIntelligenceFinalOutput(run_id=run_id, status="error", document_type="unknown", audit_summary=ingest.get("error", "Ingestion failed"), agents_used=agents_used)

        # Step 2: Classification
        s2 = collector.start_step(tracked_id, "DocumentClassifierAgent", 1)
        classification = await document_classifier_agent(request.content, request.document_type_hint, lang)
        collector.end_step(s2)
        agents_used.append("DocumentClassifierAgent")
        doc_type = classification["document_type"]
        confidence = classification["confidence"]
        actions.append(f"classified: {doc_type} ({confidence:.0%})")

        # Step 3: Extraction
        s3 = collector.start_step(tracked_id, "SchemaExtractionAgent", 2)
        extraction = await schema_extraction_agent(request.content, doc_type, lang)
        collector.end_step(s3)
        agents_used.append("SchemaExtractionAgent")
        fields = extraction["fields"]
        actions.append(f"extracted: {extraction['field_count']} fields")

        # Step 4: Validation
        s4 = collector.start_step(tracked_id, "ValidationAgent", 3)
        validation = await validation_agent(fields, doc_type, lang)
        collector.end_step(s4)
        agents_used.append("ValidationAgent")
        is_valid = validation["schema_valid"]
        errors = validation["errors"]
        error_count = validation.get("error_count", 0)
        actions.append(f"validation: {'valid' if is_valid else str(error_count) + ' errors'}")

        # Step 5: Summary
        s5 = collector.start_step(tracked_id, "SummaryAgent", 4)
        summary_result = await summary_agent(request.content, doc_type, fields, lang)
        collector.end_step(s5)
        agents_used.append("SummaryAgent")
        actions.append(f"summary: {summary_result['word_count']} words")

        # Step 6: Storage
        s6 = collector.start_step(tracked_id, "StorageAgent", 5)
        storage = await storage_agent(run_id, doc_type, fields, summary_result["summary"], lang)
        collector.end_step(s6)
        agents_used.append("StorageAgent")
        actions.append(f"stored: {storage['storage_id']}")

        # Step 7: Supervisor
        s7 = collector.start_step(tracked_id, "SupervisorAgent", 6)
        supervisor = await supervisor_agent(doc_type, fields, is_valid, errors, summary_result["summary"], confidence, lang)
        collector.end_step(s7, provider=supervisor.get("provider", ""), tokens=supervisor.get("total_tokens", 0), cost=supervisor.get("cost_usd", 0.0))
        agents_used.append("SupervisorAgent")
        actions.append(f"supervisor: {supervisor['approval']}")

        # Propagate LLM usage from supervisor
        total_tokens = supervisor.get("total_tokens", 0)
        total_cost = supervisor.get("cost_usd", 0.0)
        provider_used = supervisor.get("provider", "none")
        model_used = supervisor.get("model", "none")
        llm_used = supervisor.get("llm_used", False)

        collector.end_run(tracked_id)

        return DocumentIntelligenceFinalOutput(
            run_id=run_id, status="completed", document_type=doc_type,
            extracted_fields=fields, schema_valid=is_valid,
            validation_errors=errors, summary=summary_result["summary"],
            key_points=summary_result["key_points"],
            requires_human_review=supervisor["requires_human_review"],
            agents_used=agents_used, actions_taken=actions,
            processing_time_ms=round((time.time() - start_time) * 1000, 1),
            audit_summary=supervisor["audit_summary"],
            provider=provider_used,
            model=model_used,
            total_tokens=total_tokens,
            tokens_input=supervisor.get("tokens_input", 0),
            tokens_output=supervisor.get("tokens_output", 0),
            cost_usd=total_cost,
            llm_used=llm_used,
        )
    except Exception as e:
        collector.end_run(tracked_id, status="failed")
        return DocumentIntelligenceFinalOutput(
            run_id=run_id, status="error", document_type="unknown",
            audit_summary=str(e), agents_used=agents_used,
            processing_time_ms=round((time.time() - start_time) * 1000, 1),
        )
