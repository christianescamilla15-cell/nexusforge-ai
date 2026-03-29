"""Bilingual prompt templates for Document Intelligence agents."""

CLASSIFIER_PROMPT = {
    "es": """Clasifica el siguiente documento en una de estas categorías:
- contract (contrato)
- policy (política)
- invoice (factura)
- resume (currículum)
- report (reporte)
- unknown

Responde SOLO con la categoría en inglés.

Documento:
{content}""",
    "en": """Classify the following document into one of these categories:
- contract
- policy
- invoice
- resume
- report
- unknown

Respond ONLY with the category.

Document:
{content}""",
}

EXTRACTION_PROMPTS = {
    "contract": {
        "es": "Extrae: partes involucradas, fecha de inicio, fecha de fin, valor del contrato, tipo de servicio, cláusulas principales, nivel de soporte.",
        "en": "Extract: parties involved, start date, end date, contract value, service type, key clauses, support level.",
    },
    "policy": {
        "es": "Extrae: nombre de la política, fecha de vigencia, alcance, requisitos, excepciones, responsables.",
        "en": "Extract: policy name, effective date, scope, requirements, exceptions, responsible parties.",
    },
    "invoice": {
        "es": "Extrae: número de factura, emisor, receptor, fecha, items/servicios, subtotal, impuestos, total, método de pago.",
        "en": "Extract: invoice number, issuer, recipient, date, items/services, subtotal, taxes, total, payment method.",
    },
    "resume": {
        "es": "Extrae: nombre completo, email, teléfono, ubicación, experiencia laboral, educación, habilidades, idiomas.",
        "en": "Extract: full name, email, phone, location, work experience, education, skills, languages.",
    },
    "report": {
        "es": "Extrae: título, autor, fecha, resumen ejecutivo, hallazgos principales, recomendaciones, métricas.",
        "en": "Extract: title, author, date, executive summary, key findings, recommendations, metrics.",
    },
}

VALIDATION_PROMPT = {
    "es": "Valida que los campos extraídos sean consistentes, completos y no contengan datos obviamente incorrectos.",
    "en": "Validate that extracted fields are consistent, complete, and do not contain obviously incorrect data.",
}

SUMMARY_PROMPT = {
    "es": "Genera un resumen conciso del documento en 3-5 oraciones. Incluye los puntos clave más relevantes.",
    "en": "Generate a concise summary of the document in 3-5 sentences. Include the most relevant key points.",
}

SUPERVISOR_PROMPT = {
    "es": "Revisa la clasificación, extracción, validación y resumen. Determina si el resultado es confiable o requiere revisión humana.",
    "en": "Review the classification, extraction, validation, and summary. Determine if the result is reliable or requires human review.",
}
