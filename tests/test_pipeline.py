"""Offline tests for the triage -> fraud handoff (agents are stubbed)."""

from bank_triage.pipeline import TriagePipeline
from bank_triage.routing import route
from bank_triage.schemas import (
    Category,
    Channel,
    Confidence,
    FraudAnalysis,
    FraudType,
    InboundMessage,
    Priority,
    RiskLevel,
)

from .test_routing import make

MSG = InboundMessage(message_id="m1", channel=Channel.SECURE_CHAT, body="...")

ANALYSIS = FraudAnalysis(
    fraud_type=FraudType.ACCOUNT_TAKEOVER,
    secondary_fraud_types=[],
    attack_vector="v",
    evidence=[],
    estimated_exposure=None,
    risk_level=RiskLevel.HIGH,
    confidence=Confidence.HIGH,
    tactical_actions=[],
    permanent_fixes=[],
    customer_guidance=[],
    escalate_to_financial_crimes=False,
    regulatory_considerations=[],
    analyst_summary="s",
)


class StubTriage:
    def __init__(self, triage):
        self.triage_result = triage

    def triage(self, message):
        return route(message, self.triage_result)


class StubFraud:
    def __init__(self):
        self.calls = 0

    def analyze(self, message, triage):
        self.calls += 1
        return ANALYSIS


def test_fraud_case_gets_analysis():
    fraud = StubFraud()
    pipeline = TriagePipeline(StubTriage(make(Category.FRAUD_SECURITY, Priority.HIGH)), fraud)
    decision = pipeline.process(MSG)
    assert decision.queue == "fraud-ops"
    assert decision.fraud_analysis == ANALYSIS
    assert fraud.calls == 1


def test_secondary_fraud_signal_also_analysed():
    fraud = StubFraud()
    triage = make(Category.ACCOUNT_SERVICES, Priority.MEDIUM, secondary=[Category.FRAUD_SECURITY])
    decision = TriagePipeline(StubTriage(triage), fraud).process(MSG)
    assert decision.fraud_analysis is not None


def test_non_fraud_case_skips_fraud_agent():
    fraud = StubFraud()
    pipeline = TriagePipeline(StubTriage(make(Category.GENERAL_INQUIRY, Priority.LOW)), fraud)
    decision = pipeline.process(MSG)
    assert decision.fraud_analysis is None
    assert fraud.calls == 0
