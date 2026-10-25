"""End-to-end workflow: triage every message, then analyse the fraud cases."""

from __future__ import annotations

import logging

from .classifier_agent import TriageAgent
from .fraud_agent import FraudAnalysisAgent
from .routing import FRAUD_QUEUE
from .schemas import InboundMessage, RoutingDecision

logger = logging.getLogger(__name__)


class TriagePipeline:
    def __init__(
        self,
        triage_agent: TriageAgent | None = None,
        fraud_agent: FraudAnalysisAgent | None = None,
    ) -> None:
        self.triage_agent = triage_agent or TriageAgent()
        self.fraud_agent = fraud_agent or FraudAnalysisAgent()

    def process(self, message: InboundMessage) -> RoutingDecision:
        decision = self.triage_agent.triage(message)
        if decision.queue == FRAUD_QUEUE:
            logger.info("[%s] handing off to fraud agent", message.message_id)
            decision.fraud_analysis = self.fraud_agent.analyze(message, decision.triage)
        return decision
