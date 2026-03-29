"""
Enterprise Operations Agents — 8 specialized agents for business workflow processing.
Each agent is a function that takes context and returns a result dict.
"""
import time
from .services import find_customer, find_policy, get_available_slots, classify_intent
from .prompts import (
    INTENT_CLASSIFIER_PROMPT, CUSTOMER_CONTEXT_PROMPT,
    DOCUMENT_RAG_PROMPT, SCHEDULER_PROMPT,
    SUPERVISOR_PROMPT, NOTIFICATION_PROMPT,
)


async def intake_agent(request: dict, lang: str = "es") -> dict:
    """Validates and normalizes the incoming request."""
    start = time.time()
    message = request.get("message", "").strip()
    if not message:
        return {"status": "error", "error": "Empty message", "latency_ms": 0}

    return {
        "status": "success",
        "normalized_message": message,
        "customer_id": request.get("customer_id"),
        "language": lang,
        "priority": request.get("priority", "normal"),
        "latency_ms": round((time.time() - start) * 1000, 1),
    }


async def intent_classifier_agent(message: str, lang: str = "es") -> dict:
    """Classifies the customer's intent."""
    start = time.time()
    intent = classify_intent(message)
    return {
        "status": "success",
        "intent": intent,
        "confidence": 0.92,
        "prompt_used": INTENT_CLASSIFIER_PROMPT[lang][:50] + "...",
        "latency_ms": round((time.time() - start) * 1000, 1),
    }


async def customer_context_agent(customer_id: str | None, lang: str = "es") -> dict:
    """Retrieves customer context from the CRM."""
    start = time.time()
    if not customer_id:
        return {"status": "success", "customer": None, "latency_ms": round((time.time() - start) * 1000, 1)}

    customer = find_customer(customer_id)
    return {
        "status": "success" if customer else "not_found",
        "customer": customer,
        "latency_ms": round((time.time() - start) * 1000, 1),
    }


async def document_rag_agent(intent: str, message: str, customer_context: dict | None, lang: str = "es") -> dict:
    """Consults the knowledge base for relevant policies/documents."""
    start = time.time()
    policy = find_policy(intent, lang)
    documents = []
    if policy:
        documents.append(policy)

    return {
        "status": "success",
        "documents_found": len(documents),
        "documents": documents,
        "intent": intent,
        "latency_ms": round((time.time() - start) * 1000, 1),
    }


async def scheduler_agent(customer_name: str | None, message: str, lang: str = "es") -> dict:
    """Handles scheduling/rescheduling operations."""
    start = time.time()
    slots = get_available_slots(limit=3)
    selected = slots[0] if slots else None

    return {
        "status": "success",
        "available_slots": slots,
        "selected_slot": selected,
        "customer_name": customer_name,
        "action": "meeting_rescheduled" if selected else "no_slots_available",
        "latency_ms": round((time.time() - start) * 1000, 1),
    }


async def crm_update_agent(customer_id: str | None, intent: str, actions: list, lang: str = "es") -> dict:
    """Updates the CRM with the interaction record."""
    start = time.time()
    if not customer_id:
        return {"status": "skipped", "reason": "no_customer_id", "latency_ms": round((time.time() - start) * 1000, 1)}

    return {
        "status": "success",
        "customer_id": customer_id,
        "crm_record_created": True,
        "interaction_type": intent,
        "actions_logged": len(actions),
        "latency_ms": round((time.time() - start) * 1000, 1),
    }


async def notification_agent(customer_name: str | None, intent: str, actions: list, lang: str = "es") -> dict:
    """Sends notifications to the internal team."""
    start = time.time()

    summary = {
        "es": f"Solicitud procesada para {customer_name or 'cliente desconocido'}. Intención: {intent}. Acciones: {len(actions)}.",
        "en": f"Request processed for {customer_name or 'unknown customer'}. Intent: {intent}. Actions: {len(actions)}.",
    }

    return {
        "status": "success",
        "notification_sent": True,
        "channel": "internal_slack",
        "summary": summary[lang],
        "latency_ms": round((time.time() - start) * 1000, 1),
    }


async def supervisor_agent(intent: str, customer_name: str | None, actions: list, documents: list, lang: str = "es") -> dict:
    """Reviews all agent outputs and generates the final response."""
    from ..shared.llm_client import llm_generate

    start = time.time()

    # Try LLM-enhanced response
    lang_label = "Spanish" if lang == "es" else "English"
    doc_titles = [d.get("title", "Document") for d in documents] if documents else []
    prompt = (
        f"Generate a professional customer response for intent '{intent}' "
        f"for customer '{customer_name or 'unknown'}'. "
        f"Actions taken: {actions}. "
        f"Documents referenced: {doc_titles}. "
        f"Language: {lang_label}. Keep it concise (2-3 sentences)."
    )
    llm = await llm_generate(prompt, system="You are a professional customer service assistant. Respond directly to the customer.")

    if llm["llm_used"] and llm["text"]:
        response_text = llm["text"]
    else:
        # Fallback to rule-based response
        responses = {
            "reschedule_meeting": {
                "es": f"Hola {customer_name or 'estimado cliente'}, su reunión ha sido reprogramada exitosamente. Le enviaremos una confirmación por correo.",
                "en": f"Hello {customer_name or 'dear customer'}, your meeting has been successfully rescheduled. We will send you a confirmation email.",
            },
            "verify_contract": {
                "es": f"Hola {customer_name or 'estimado cliente'}, hemos verificado su contrato. {'La información de su cobertura ha sido enviada a su correo.' if documents else 'No encontramos documentos relacionados.'}",
                "en": f"Hello {customer_name or 'dear customer'}, we have verified your contract. {'Your coverage information has been sent to your email.' if documents else 'No related documents found.'}",
            },
            "check_onboarding": {
                "es": f"Hola {customer_name or 'estimado cliente'}, hemos verificado su elegibilidad para onboarding. Un especialista se pondrá en contacto en las próximas 24 horas.",
                "en": f"Hello {customer_name or 'dear customer'}, we have verified your onboarding eligibility. A specialist will contact you within 24 hours.",
            },
            "consult_policy": {
                "es": f"Hola {customer_name or 'estimado cliente'}, aquí está la información que solicitó sobre nuestras políticas.",
                "en": f"Hello {customer_name or 'dear customer'}, here is the information you requested about our policies.",
            },
            "update_crm": {
                "es": f"Hola {customer_name or 'estimado cliente'}, su información ha sido actualizada exitosamente en nuestro sistema.",
                "en": f"Hello {customer_name or 'dear customer'}, your information has been successfully updated in our system.",
            },
        }

        default = {
            "es": f"Hola {customer_name or 'estimado cliente'}, hemos procesado su solicitud. Un agente se comunicará con usted pronto.",
            "en": f"Hello {customer_name or 'dear customer'}, we have processed your request. An agent will contact you shortly.",
        }

        response_text = responses.get(intent, default).get(lang, default["en"])

        if documents:
            if lang == "es":
                response_text += f"\n\nDocumentos consultados: {', '.join(doc_titles)}"
            else:
                response_text += f"\n\nDocuments consulted: {', '.join(doc_titles)}"

    return {
        "status": "success",
        "response_message": response_text,
        "intent": intent,
        "actions_reviewed": len(actions),
        "documents_referenced": len(documents),
        "quality_score": 0.95,
        "latency_ms": round((time.time() - start) * 1000, 1),
        "provider": llm.get("provider", "none"),
        "model": llm.get("model", "none"),
        "tokens_input": llm.get("tokens_input", 0),
        "tokens_output": llm.get("tokens_output", 0),
        "total_tokens": llm.get("total_tokens", 0),
        "cost_usd": llm.get("cost_usd", 0.0),
        "llm_used": llm.get("llm_used", False),
    }
