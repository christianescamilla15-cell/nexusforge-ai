"""Service layer for Portfolio Copilot — project retrieval, comparison, skill mapping."""
import json
from pathlib import Path
from typing import Optional

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def load_projects() -> list:
    with open(FIXTURES_DIR / "portfolio_projects.json", encoding="utf-8") as f:
        return json.load(f)

def load_interview_questions() -> list:
    with open(FIXTURES_DIR / "interview_questions.json", encoding="utf-8") as f:
        return json.load(f)

def find_project(project_id: str) -> dict | None:
    return next((p for p in load_projects() if p["id"] == project_id), None)

def classify_question(question: str) -> str:
    lower = question.lower()
    if any(w in lower for w in ["compara", "compare", "vs", "diferencia", "difference"]):
        return "comparison"
    if any(w in lower for w in ["habilidad", "skill", "experiencia", "experience", "demuestr"]):
        return "skills_mapping"
    if any(w in lower for w in ["mejor", "best", "cuál", "which", "recomienda"]):
        return "best_project"
    if any(w in lower for w in ["cómo", "how", "explica", "explain", "qué es", "what is"]):
        return "technical_deep_dive"
    return "general"

def search_projects(query: str, lang: str = "es") -> list:
    projects = load_projects()
    lower = query.lower()
    scored = []
    for p in projects:
        score = 0
        desc = p.get(f"description_{lang}", p.get("description_en", "")).lower()
        for word in lower.split():
            if word in desc: score += 2
            if word in " ".join(p.get("strengths", [])).lower(): score += 3
            if word in " ".join(p.get("stack", [])).lower(): score += 1
            if word in p.get("name", "").lower(): score += 5
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]

def get_all_skills() -> list:
    projects = load_projects()
    skills = set()
    for p in projects:
        skills.update(p.get("stack", []))
        skills.update(p.get("strengths", []))
    return sorted(skills)

def find_best_project_for(capability: str) -> dict | None:
    projects = load_projects()
    for p in projects:
        if capability.lower() in [s.lower() for s in p.get("strengths", [])]:
            return p
    results = search_projects(capability)
    return results[0] if results else None

def compare_projects(id_a: str, id_b: str, lang: str = "es") -> dict:
    a = find_project(id_a)
    b = find_project(id_b)
    if not a or not b:
        return {"error": "Project not found"}
    desc_key = f"description_{lang}"
    return {
        "project_a": {"name": a["name"], "type": a["type"], "description": a.get(desc_key, a.get("description_en", "")), "stack": a["stack"], "strengths": a["strengths"], "metrics": a["metrics"]},
        "project_b": {"name": b["name"], "type": b["type"], "description": b.get(desc_key, b.get("description_en", "")), "stack": b["stack"], "strengths": b["strengths"], "metrics": b["metrics"]},
        "shared_stack": sorted(set(a["stack"]) & set(b["stack"])),
        "shared_strengths": sorted(set(a["strengths"]) & set(b["strengths"])),
        "unique_a": sorted(set(a["strengths"]) - set(b["strengths"])),
        "unique_b": sorted(set(b["strengths"]) - set(a["strengths"])),
    }
