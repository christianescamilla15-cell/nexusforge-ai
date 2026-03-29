"""Portfolio Copilot Agents — 6 specialized agents for portfolio intelligence."""
import time
from .services import classify_question, search_projects, get_all_skills, find_best_project_for, compare_projects, load_projects

async def router_agent(question: str, lang: str = "es") -> dict:
    start = time.time()
    q_type = classify_question(question)
    return {"status": "success", "question_type": q_type, "latency_ms": round((time.time() - start) * 1000, 1)}

async def portfolio_rag_agent(question: str, q_type: str, lang: str = "es") -> dict:
    start = time.time()
    results = search_projects(question, lang)
    desc_key = f"description_{lang}"
    return {
        "status": "success",
        "results_found": len(results),
        "top_projects": [{"name": p["name"], "id": p["id"], "type": p["type"], "description": p.get(desc_key, p.get("description_en", "")), "strengths": p["strengths"][:5]} for p in results[:3]],
        "latency_ms": round((time.time() - start) * 1000, 1),
    }

async def project_comparison_agent(question: str, projects: list, lang: str = "es") -> dict:
    start = time.time()
    if len(projects) >= 2:
        comparison = compare_projects(projects[0]["id"], projects[1]["id"], lang)
    else:
        comparison = {"note": "Not enough projects to compare"}
    return {"status": "success", "comparison": comparison, "latency_ms": round((time.time() - start) * 1000, 1)}

async def skills_mapper_agent(question: str, projects: list, lang: str = "es") -> dict:
    start = time.time()
    all_skills = get_all_skills()
    project_skills = {}
    for p in projects[:5]:
        project_skills[p["name"]] = p.get("strengths", [])[:5]
    relevant = [s for s in all_skills if any(w in s.lower() for w in question.lower().split() if len(w) > 3)]
    return {
        "status": "success",
        "all_skills_count": len(all_skills),
        "relevant_skills": relevant[:10] if relevant else all_skills[:10],
        "project_skills": project_skills,
        "latency_ms": round((time.time() - start) * 1000, 1),
    }

async def response_formatter_agent(q_type: str, question: str, rag_results: list, comparison: dict, skills: dict, lang: str = "es") -> dict:
    start = time.time()
    top = rag_results[0] if rag_results else None

    answers = {
        "best_project": {
            "es": f"El proyecto más relevante es **{top['name']}** ({top['type']}). {top['description']}. Fortalezas clave: {', '.join(top['strengths'][:3])}." if top else "No se encontró un proyecto que coincida con la consulta.",
            "en": f"The most relevant project is **{top['name']}** ({top['type']}). {top['description']}. Key strengths: {', '.join(top['strengths'][:3])}." if top else "No matching project found.",
        },
        "comparison": {
            "es": f"Comparación entre {comparison.get('comparison', {}).get('project_a', {}).get('name', '?')} y {comparison.get('comparison', {}).get('project_b', {}).get('name', '?')}. Stack compartido: {', '.join(comparison.get('comparison', {}).get('shared_stack', []))}.",
            "en": f"Comparison between {comparison.get('comparison', {}).get('project_a', {}).get('name', '?')} and {comparison.get('comparison', {}).get('project_b', {}).get('name', '?')}. Shared stack: {', '.join(comparison.get('comparison', {}).get('shared_stack', []))}.",
        },
        "skills_mapping": {
            "es": f"El portafolio demuestra {skills.get('all_skills_count', 0)} habilidades/fortalezas. Las más relevantes: {', '.join(skills.get('relevant_skills', [])[:5])}.",
            "en": f"The portfolio demonstrates {skills.get('all_skills_count', 0)} skills/strengths. Most relevant: {', '.join(skills.get('relevant_skills', [])[:5])}.",
        },
        "technical_deep_dive": {
            "es": f"{'Basado en ' + top['name'] + ': ' + top['description'] if top else 'No se encontró información técnica específica para esta consulta.'}",
            "en": f"{'Based on ' + top['name'] + ': ' + top['description'] if top else 'No specific technical information found for this query.'}",
        },
    }
    default = {"es": f"{'El proyecto más relevante es ' + top['name'] + '.' if top else 'Consulta procesada.'}", "en": f"{'The most relevant project is ' + top['name'] + '.' if top else 'Query processed.'}"}
    answer = answers.get(q_type, default).get(lang, default["en"])
    recommended = top["name"] if top else None
    supporting = [p["name"] for p in rag_results[:3]]
    related = skills.get("relevant_skills", [])[:8]

    return {"status": "success", "final_answer": answer, "recommended_project": recommended, "supporting_projects": supporting, "related_skills": related, "latency_ms": round((time.time() - start) * 1000, 1)}

async def supervisor_agent(q_type: str, answer: str, projects_found: int, lang: str = "es") -> dict:
    from ..shared.llm_client import llm_generate

    start = time.time()
    requires_review = projects_found == 0 or q_type == "general"

    # Try LLM-enhanced audit summary
    lang_label = "Spanish" if lang == "es" else "English"
    prompt = (
        f"Generate a brief audit summary for a portfolio query. "
        f"Query type: '{q_type}', Projects found: {projects_found}, "
        f"Requires review: {requires_review}. "
        f"Language: {lang_label}. Keep it to 1-2 sentences."
    )
    llm = await llm_generate(prompt, system="You are a portfolio intelligence auditor. Be concise.")

    if llm["llm_used"] and llm["text"]:
        audit_text = llm["text"]
    else:
        # Fallback to rule-based audit
        audit = {
            "es": f"Consulta tipo '{q_type}' procesada. {projects_found} proyectos relevantes encontrados. {'Requiere revision.' if requires_review else 'Respuesta generada automaticamente.'}",
            "en": f"Query type '{q_type}' processed. {projects_found} relevant projects found. {'Requires review.' if requires_review else 'Response auto-generated.'}",
        }
        audit_text = audit[lang]

    return {
        "status": "success",
        "requires_human_review": requires_review,
        "audit_summary": audit_text,
        "latency_ms": round((time.time() - start) * 1000, 1),
        "provider": llm.get("provider", "none"),
        "model": llm.get("model", "none"),
        "tokens_input": llm.get("tokens_input", 0),
        "tokens_output": llm.get("tokens_output", 0),
        "total_tokens": llm.get("total_tokens", 0),
        "cost_usd": llm.get("cost_usd", 0.0),
        "llm_used": llm.get("llm_used", False),
    }
