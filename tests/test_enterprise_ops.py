"""Tests for Enterprise Operations use case."""
import pytest
import asyncio
from backend.app.use_cases.enterprise_ops.services import (
    find_customer, find_policy, get_available_slots, classify_intent,
    load_customers, load_policies, load_calendar,
)
from backend.app.use_cases.enterprise_ops.schemas import OperationsRequest, OperationsResponse


class TestServices:
    def test_load_customers(self):
        customers = load_customers()
        assert len(customers) >= 5
        assert all("id" in c for c in customers)

    def test_load_policies(self):
        policies = load_policies()
        assert len(policies) >= 4
        assert all("id" in p for p in policies)

    def test_load_calendar(self):
        calendar = load_calendar()
        assert len(calendar) >= 3
        assert all("slots" in d for d in calendar)

    def test_find_customer_exists(self):
        customer = find_customer("CUST-001")
        assert customer is not None
        assert customer["name"] == "María González"

    def test_find_customer_not_exists(self):
        customer = find_customer("CUST-999")
        assert customer is None

    def test_find_policy_reschedule(self):
        policy = find_policy("reschedule_meeting", "es")
        assert policy is not None
        assert "POL-001" == policy["id"]

    def test_find_policy_english(self):
        policy = find_policy("verify_contract", "en")
        assert policy is not None

    def test_get_available_slots(self):
        slots = get_available_slots(limit=3)
        assert len(slots) == 3
        assert all(" " in s for s in slots)


class TestIntentClassification:
    def test_reschedule(self):
        assert classify_intent("Necesito reprogramar mi reunión") == "reschedule_meeting"

    def test_contract(self):
        assert classify_intent("Check my contract coverage") == "verify_contract"

    def test_onboarding(self):
        assert classify_intent("¿Soy elegible para onboarding?") == "check_onboarding"

    def test_policy(self):
        assert classify_intent("What is the cancellation policy?") == "consult_policy"

    def test_crm(self):
        assert classify_intent("Actualizar mi plan en el CRM") == "update_crm"

    def test_general(self):
        assert classify_intent("Hello, I have a question") == "general_inquiry"


class TestSchemas:
    def test_request_defaults(self):
        req = OperationsRequest(message="test")
        assert req.language == "es"
        assert req.priority == "normal"

    def test_response_structure(self):
        resp = OperationsResponse(run_id="123", status="completed", intent="test")
        assert resp.actions_taken == []
        assert resp.crm_updated is False
