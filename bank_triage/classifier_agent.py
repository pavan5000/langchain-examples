"""Triage stage: a Deep Agent driven by the `bank-triage` skill."""

from __future__ import annotations

import logging
import time

from .routing import route
from .schemas import InboundMessage, RoutingDecision, TriageResult
from .skill_agent import MODEL, build_skill_agent, format_message, log_agent_steps
from .tools import TRIAGE_TOOLS

logger = logging.getLogger(__name__)

SKILL = "bank-triage"


def build_triage_agent():
    return build_skill_agent(
        skill_set="triage",
        skill=SKILL,
        tools=TRIAGE_TOOLS,
        response_schema=TriageResult,
        # Classification is a routine task; low effort keeps latency and cost down.
        reasoning_effort="low",
        max_tokens=4096,
    )


class TriageAgent:
    def __init__(self) -> None:
        self._agent = build_triage_agent()

    def classify(self, message: InboundMessage) -> TriageResult:
        prompt = format_message(message)
        logger.info("[%s] classifying %s message (skill=%s, model=%s)", message.message_id,
                    message.channel.value, SKILL, MODEL)
        logger.debug("[%s] prompt sent to model (card numbers masked):\n%s",
                     message.message_id, prompt)

        started = time.perf_counter()
        state = self._agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        elapsed = time.perf_counter() - started

        if logger.isEnabledFor(logging.DEBUG):
            log_agent_steps(logger, message.message_id, state["messages"])
        result: TriageResult = state["structured_response"]
        logger.info("[%s] classified as %s/%s priority=%s confidence=%s in %.2fs",
                    message.message_id, result.category.value, result.sub_intent,
                    result.priority.value, result.confidence.value, elapsed)
        logger.debug("[%s] structured output:\n%s", message.message_id,
                     result.model_dump_json(indent=2))
        return result

    def triage(self, message: InboundMessage) -> RoutingDecision:
        return route(message, self.classify(message))
