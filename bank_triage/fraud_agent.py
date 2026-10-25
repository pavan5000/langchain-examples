"""Fraud stage: a Deep Agent driven by the `fraud-analysis` skill."""

from __future__ import annotations

import logging
import time

from .schemas import FraudAnalysis, InboundMessage, TriageResult
from .skill_agent import MODEL, build_skill_agent, format_message, log_agent_steps
from .tools import FRAUD_TOOLS

logger = logging.getLogger(__name__)

SKILL = "fraud-analysis"


def build_fraud_agent():
    return build_skill_agent(
        skill_set="fraud",
        skill=SKILL,
        tools=FRAUD_TOOLS,
        response_schema=FraudAnalysis,
        # Fraud analysis needs more reasoning than triage.
        reasoning_effort="medium",
        max_tokens=8192,
    )


def format_case(message: InboundMessage, triage: TriageResult) -> str:
    return (
        f"{format_message(message)}\n\n"
        f"<triage_result>\n{triage.model_dump_json(indent=2)}\n</triage_result>"
    )


class FraudAnalysisAgent:
    def __init__(self) -> None:
        self._agent = build_fraud_agent()

    def analyze(self, message: InboundMessage, triage: TriageResult) -> FraudAnalysis:
        prompt = format_case(message, triage)
        logger.info("[%s] fraud analysis started (skill=%s, model=%s)", message.message_id,
                    SKILL, MODEL)
        logger.debug("[%s] fraud case sent to model:\n%s", message.message_id, prompt)

        started = time.perf_counter()
        state = self._agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        elapsed = time.perf_counter() - started

        if logger.isEnabledFor(logging.DEBUG):
            log_agent_steps(logger, message.message_id, state["messages"])
        result: FraudAnalysis = state["structured_response"]
        logger.info("[%s] fraud type=%s risk=%s confidence=%s escalate=%s in %.2fs",
                    message.message_id, result.fraud_type.value, result.risk_level.value,
                    result.confidence.value, result.escalate_to_financial_crimes, elapsed)
        logger.debug("[%s] fraud analysis:\n%s", message.message_id,
                     result.model_dump_json(indent=2))
        return result
