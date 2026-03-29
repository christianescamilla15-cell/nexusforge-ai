"""Bilingual prompt templates for Portfolio Copilot agents."""

ROUTER_PROMPT = {
    "es": "Clasifica esta pregunta sobre el portafolio: {question}\nTipos: best_project, comparison, skills_mapping, technical_deep_dive, general",
    "en": "Classify this portfolio question: {question}\nTypes: best_project, comparison, skills_mapping, technical_deep_dive, general",
}

RAG_PROMPT = {
    "es": "Busca proyectos relevantes para responder: {question}\nTipo de consulta: {q_type}",
    "en": "Search relevant projects to answer: {question}\nQuery type: {q_type}",
}

COMPARISON_PROMPT = {
    "es": "Compara técnicamente estos proyectos: {project_a} vs {project_b}",
    "en": "Technically compare these projects: {project_a} vs {project_b}",
}

SKILLS_PROMPT = {
    "es": "Mapea las habilidades demostradas en el portafolio relevantes para: {question}",
    "en": "Map portfolio skills relevant to: {question}",
}

FORMATTER_PROMPT = {
    "es": "Genera una respuesta estructurada y profesional basada en los resultados de los agentes.",
    "en": "Generate a structured, professional response based on agent results.",
}

SUPERVISOR_PROMPT = {
    "es": "Revisa la respuesta generada. Determina si es confiable o requiere revisión humana.",
    "en": "Review the generated response. Determine if it is reliable or requires human review.",
}
