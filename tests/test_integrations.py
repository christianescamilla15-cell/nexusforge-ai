"""Tests for the integration layer."""
import pytest
import sys
import os

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


class TestIntegrationConfig:
    def test_status_returns_all_integrations(self):
        from app.integrations.config import IntegrationConfig
        status = IntegrationConfig.status()
        assert "google_drive" in status
        assert "gmail" in status
        assert "google_calendar" in status
        assert "notion" in status
        assert "webhooks" in status

    def test_each_integration_has_configured_and_type(self):
        from app.integrations.config import IntegrationConfig
        status = IntegrationConfig.status()
        for name, info in status.items():
            assert "configured" in info, f"{name} missing 'configured'"
            assert "type" in info, f"{name} missing 'type'"
            assert isinstance(info["configured"], bool), f"{name} configured should be bool"

    def test_unconfigured_by_default(self):
        """Without env vars, all should be unconfigured."""
        from app.integrations.config import IntegrationConfig
        status = IntegrationConfig.status()
        # At least some should be unconfigured in test env
        assert not all(info["configured"] for info in status.values())

    def test_status_types_are_strings(self):
        from app.integrations.config import IntegrationConfig
        status = IntegrationConfig.status()
        for name, info in status.items():
            assert isinstance(info["type"], str), f"{name} type should be str"


class TestIntegrationClientsGraceful:
    """Verify each client returns not_configured gracefully without credentials."""

    @pytest.mark.asyncio
    async def test_drive_list_files_not_configured(self):
        from app.integrations.google_drive.client import list_files
        result = await list_files()
        assert result["status"] == "not_configured"
        assert "files" in result

    @pytest.mark.asyncio
    async def test_gmail_list_messages_not_configured(self):
        from app.integrations.gmail.client import list_messages
        result = await list_messages()
        assert result["status"] == "not_configured"
        assert "messages" in result

    @pytest.mark.asyncio
    async def test_calendar_list_events_not_configured(self):
        from app.integrations.google_calendar.client import list_events
        result = await list_events()
        assert result["status"] == "not_configured"
        assert "events" in result

    @pytest.mark.asyncio
    async def test_calendar_availability_not_configured(self):
        from app.integrations.google_calendar.client import get_availability
        result = await get_availability()
        assert result["status"] == "not_configured"

    @pytest.mark.asyncio
    async def test_notion_write_not_configured(self):
        from app.integrations.notion.client import write_page
        result = await write_page(title="Test", content="test")
        assert result["status"] == "not_configured"

    @pytest.mark.asyncio
    async def test_notion_query_not_configured(self):
        from app.integrations.notion.client import query_database
        result = await query_database()
        assert result["status"] == "not_configured"
        assert "results" in result

    @pytest.mark.asyncio
    async def test_webhook_send_not_configured(self):
        from app.integrations.webhooks.client import send_webhook
        result = await send_webhook(event_type="test", payload={"test": True})
        assert result["status"] == "not_configured"


class TestFeedbackService:
    def test_feedback_stats_empty(self):
        from app.services.feedback_service import get_feedback_stats
        stats = get_feedback_stats()
        assert "total" in stats
        assert "avg_rating" in stats
        assert "approval_rate" in stats

    def test_agent_performance_empty(self):
        from app.services.feedback_service import get_agent_performance
        agents = get_agent_performance()
        assert isinstance(agents, list)

    def test_recommendations_empty(self):
        from app.services.feedback_service import get_agent_recommendations
        recs = get_agent_recommendations()
        assert "status" in recs

    def test_feedback_stats_shape(self):
        from app.services.feedback_service import get_feedback_stats
        stats = get_feedback_stats()
        assert "by_workflow" in stats
        assert isinstance(stats["by_workflow"], dict)
