import pytest
from backend.app.use_cases.portfolio_copilot.services import (
    load_projects, load_interview_questions, find_project,
    classify_question, search_projects, get_all_skills,
    find_best_project_for, compare_projects,
)
from backend.app.use_cases.portfolio_copilot.schemas import PortfolioCopilotInput, PortfolioCopilotFinalOutput

class TestServices:
    def test_load_projects(self):
        projects = load_projects()
        assert len(projects) >= 7

    def test_load_questions(self):
        questions = load_interview_questions()
        assert len(questions) >= 6

    def test_find_project(self):
        p = find_project("nexusforge-ai")
        assert p is not None
        assert p["name"] == "NexusForge AI"

    def test_find_missing(self):
        assert find_project("nonexistent") is None

    def test_classify_comparison(self):
        assert classify_question("Compare NexusForge and MindScrolling") == "comparison"

    def test_classify_best(self):
        assert classify_question("Which is the best project for orchestration?") == "best_project"

    def test_classify_skills(self):
        assert classify_question("What skills are demonstrated?") == "skills_mapping"

    def test_search_projects(self):
        results = search_projects("multi-agent orchestration")
        assert len(results) > 0
        assert results[0]["id"] == "nexusforge-ai"

    def test_get_all_skills(self):
        skills = get_all_skills()
        assert len(skills) > 10

    def test_find_best_for(self):
        p = find_best_project_for("multi-agent orchestration")
        assert p is not None

    def test_compare(self):
        result = compare_projects("nexusforge-ai", "mindscrolling")
        assert "project_a" in result
        assert "project_b" in result
        assert "shared_stack" in result

class TestSchemas:
    def test_input_defaults(self):
        inp = PortfolioCopilotInput(question="test")
        assert inp.language == "es"

    def test_output_defaults(self):
        out = PortfolioCopilotFinalOutput(run_id="x", status="ok")
        assert out.supporting_projects == []
        assert out.requires_human_review is False
