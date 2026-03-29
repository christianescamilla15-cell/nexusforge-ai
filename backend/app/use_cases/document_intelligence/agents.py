"""Document Intelligence Agents — 7 specialized agents for document processing."""
import time
from .services import classify_document, extract_fields, validate_extraction, generate_summary


async def document_ingestion_agent(content: str, filename: str | None, lang: str = "es") -> dict:
    start = time.time()
    if not content or not content.strip():
        return {"status": "error", "error": "Empty document", "latency_ms": 0}
    word_count = len(content.split())
    char_count = len(content)
    return {
        "status": "success",
        "word_count": word_count,
        "char_count": char_count,
        "filename": filename or "unnamed",
        "language": lang,
        "latency_ms": round((time.time() - start) * 1000, 1),
    }


async def document_classifier_agent(content: str, type_hint: str | None = None, lang: str = "es") -> dict:
    start = time.time()
    if type_hint and type_hint in ("contract", "policy", "invoice", "resume", "report"):
        return {"status": "success", "document_type": type_hint, "confidence": 1.0, "method": "hint", "latency_ms": round((time.time() - start) * 1000, 1)}
    doc_type, confidence = classify_document(content)
    return {"status": "success", "document_type": doc_type, "confidence": confidence, "method": "classification", "latency_ms": round((time.time() - start) * 1000, 1)}


async def schema_extraction_agent(content: str, doc_type: str, lang: str = "es") -> dict:
    start = time.time()
    fields = extract_fields(content, doc_type)
    return {"status": "success", "document_type": doc_type, "fields": fields, "field_count": len(fields), "latency_ms": round((time.time() - start) * 1000, 1)}


async def validation_agent(fields: dict, doc_type: str, lang: str = "es") -> dict:
    start = time.time()
    is_valid, errors = validate_extraction(fields, doc_type)
    return {"status": "success", "schema_valid": is_valid, "errors": errors, "error_count": len(errors), "latency_ms": round((time.time() - start) * 1000, 1)}


async def summary_agent(content: str, doc_type: str, fields: dict, lang: str = "es") -> dict:
    start = time.time()
    summary, key_points = generate_summary(content, doc_type, fields, lang)
    return {"status": "success", "summary": summary, "key_points": key_points, "word_count": len(summary.split()), "latency_ms": round((time.time() - start) * 1000, 1)}


async def storage_agent(run_id: str, doc_type: str, fields: dict, summary: str, lang: str = "es") -> dict:
    start = time.time()
    return {"status": "success", "stored": True, "storage_id": f"store-{run_id[:8]}", "document_type": doc_type, "field_count": len(fields), "latency_ms": round((time.time() - start) * 1000, 1)}


async def supervisor_agent(doc_type: str, fields: dict, is_valid: bool, errors: list, summary: str, confidence: float, lang: str = "es") -> dict:
    start = time.time()
    requires_review = (not is_valid) or (confidence < 0.7) or (doc_type == "unknown") or (len(errors) > 2)

    audit = {
        "es": f"Documento tipo '{doc_type}' procesado. {'Válido' if is_valid else 'Con errores'}. {len(fields)} campos extraídos. Confianza: {confidence:.0%}. {'Requiere revisión humana.' if requires_review else 'Aprobado automáticamente.'}",
        "en": f"Document type '{doc_type}' processed. {'Valid' if is_valid else 'Has errors'}. {len(fields)} fields extracted. Confidence: {confidence:.0%}. {'Requires human review.' if requires_review else 'Auto-approved.'}",
    }

    return {"status": "success", "requires_human_review": requires_review, "audit_summary": audit[lang], "approval": "auto" if not requires_review else "pending_review", "latency_ms": round((time.time() - start) * 1000, 1)}
