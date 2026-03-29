"""Prompt templates for the Enterprise Operations Assistant — ES/EN bilingual."""

INTENT_CLASSIFIER_PROMPT = {
    "es": """Clasifica la intención del siguiente mensaje del cliente.
Categorías posibles: reschedule_meeting, verify_contract, check_onboarding, consult_policy, update_crm, general_inquiry
Responde SOLO con la categoría, sin explicación.

Mensaje: {message}""",
    "en": """Classify the intent of the following customer message.
Possible categories: reschedule_meeting, verify_contract, check_onboarding, consult_policy, update_crm, general_inquiry
Respond ONLY with the category, no explanation.

Message: {message}""",
}

CUSTOMER_CONTEXT_PROMPT = {
    "es": """Busca información del cliente con ID: {customer_id}
Nombre, plan activo, estado del contrato, fecha de renovación, y cualquier nota relevante.""",
    "en": """Look up customer information for ID: {customer_id}
Name, active plan, contract status, renewal date, and any relevant notes.""",
}

DOCUMENT_RAG_PROMPT = {
    "es": """Consulta la base de conocimiento para responder la siguiente pregunta del cliente:
Contexto del cliente: {customer_context}
Pregunta: {message}
Intención detectada: {intent}""",
    "en": """Query the knowledge base to answer the following customer question:
Customer context: {customer_context}
Question: {message}
Detected intent: {intent}""",
}

SCHEDULER_PROMPT = {
    "es": """El cliente solicita reprogramar una reunión.
Cliente: {customer_name}
Solicitud: {message}
Horarios disponibles: {available_slots}
Selecciona el mejor horario y confirma.""",
    "en": """The customer requests to reschedule a meeting.
Customer: {customer_name}
Request: {message}
Available slots: {available_slots}
Select the best time slot and confirm.""",
}

SUPERVISOR_PROMPT = {
    "es": """Revisa las acciones tomadas por los agentes y genera una respuesta final coherente para el cliente.
Intención: {intent}
Cliente: {customer_name}
Acciones realizadas: {actions}
Documentos consultados: {documents}
Idioma de respuesta: español
La respuesta debe ser profesional, concisa y útil.""",
    "en": """Review the actions taken by agents and generate a coherent final response for the customer.
Intent: {intent}
Customer: {customer_name}
Actions taken: {actions}
Documents consulted: {documents}
Response language: English
The response should be professional, concise, and helpful.""",
}

NOTIFICATION_PROMPT = {
    "es": "Genera un resumen de notificación para el equipo interno sobre la solicitud procesada del cliente {customer_name}. Intención: {intent}. Acciones: {actions}.",
    "en": "Generate a notification summary for the internal team about the processed request from customer {customer_name}. Intent: {intent}. Actions: {actions}.",
}
