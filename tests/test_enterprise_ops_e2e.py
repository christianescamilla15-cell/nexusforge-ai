"""End-to-end tests for Enterprise Operations workflow."""
import pytest
import asyncio
from backend.app.use_cases.enterprise_ops.workflow import run_enterprise_ops_workflow
from backend.app.use_cases.enterprise_ops.schemas import OperationsRequest

class TestEnterpriseOpsE2E:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_happy_path_reschedule_es(self):
        request = OperationsRequest(
            message="Necesito reprogramar mi reunión del viernes",
            customer_id="CUST-001",
            language="es",
            priority="normal",
        )
        result = self._run(run_enterprise_ops_workflow(request))
        assert result.status == "completed"
        assert result.intent == "reschedule_meeting"
        assert result.customer_name == "María González"
        assert len(result.agents_used) >= 7
        assert result.crm_updated is True
        assert result.notification_sent is True
        assert result.processing_time_ms > 0
        assert "SupervisorAgent" in result.agents_used

    def test_happy_path_contract_en(self):
        request = OperationsRequest(
            message="Can you check my support coverage?",
            customer_id="CUST-004",
            language="en",
        )
        result = self._run(run_enterprise_ops_workflow(request))
        assert result.status == "completed"
        assert result.intent == "verify_contract"
        assert result.customer_name == "James Wilson"
        assert len(result.documents_consulted) >= 1

    def test_onboarding_check(self):
        request = OperationsRequest(
            message="¿Soy elegible para onboarding gratuito?",
            customer_id="CUST-005",
            language="es",
        )
        result = self._run(run_enterprise_ops_workflow(request))
        assert result.status == "completed"
        assert result.intent == "check_onboarding"

    def test_no_customer_general(self):
        request = OperationsRequest(
            message="What are your policies?",
            language="en",
        )
        result = self._run(run_enterprise_ops_workflow(request))
        assert result.status == "completed"
        assert result.customer_name is None
        assert result.crm_updated is False

    def test_empty_message_fails(self):
        request = OperationsRequest(message="", language="es")
        result = self._run(run_enterprise_ops_workflow(request))
        assert result.status == "error"

    def test_all_agents_tracked(self):
        request = OperationsRequest(
            message="Necesito reprogramar mi cita",
            customer_id="CUST-001",
            language="es",
        )
        result = self._run(run_enterprise_ops_workflow(request))
        assert "IntakeAgent" in result.agents_used
        assert "IntentClassifierAgent" in result.agents_used
        assert "CustomerContextAgent" in result.agents_used
        assert "DocumentRAGAgent" in result.agents_used
        assert "CRMUpdateAgent" in result.agents_used
        assert "NotificationAgent" in result.agents_used
        assert "SupervisorAgent" in result.agents_used
