"""Deterministic routing: maps the LLM's TriageResult onto internal queues.

The LLM classifies; plain code decides where the ticket goes. Business rules
(e.g. "fraud is always high priority") live here so they can't be talked out
of by a cleverly worded message.
"""

from __future__ import annotations

import logging
import re

from .schemas import (
    Category,
    Confidence,
    InboundMessage,
    Priority,
    RoutingDecision,
    TriageResult,
)

logger = logging.getLogger(__name__)

QUEUES: dict[Category, str] = {
    Category.FRAUD_SECURITY: "fraud-ops",
    Category.ACCOUNT_SERVICES: "account-services",
    Category.LENDING_MORTGAGES: "lending-mortgages",
    Category.GENERAL_INQUIRY: "general-inquiries",
}
MANUAL_REVIEW_QUEUE = "triage-manual-review"
FRAUD_QUEUE = QUEUES[Category.FRAUD_SECURITY]

# Allowed priority band per category (the use case's stated policy).
PRIORITY_BANDS: dict[Category, set[Priority]] = {
    Category.FRAUD_SECURITY: {Priority.HIGH},
    Category.ACCOUNT_SERVICES: {Priority.MEDIUM, Priority.HIGH},
    Category.LENDING_MORTGAGES: {Priority.MEDIUM, Priority.LOW},
    Category.GENERAL_INQUIRY: {Priority.LOW},
}
DEFAULT_PRIORITY: dict[Category, Priority] = {
    Category.FRAUD_SECURITY: Priority.HIGH,
    Category.ACCOUNT_SERVICES: Priority.MEDIUM,
    Category.LENDING_MORTGAGES: Priority.MEDIUM,
    Category.GENERAL_INQUIRY: Priority.LOW,
}
SLA_MINUTES: dict[Priority, int] = {
    Priority.HIGH: 15,
    Priority.MEDIUM: 240,
    Priority.LOW: 1440,
}

# 13-19 digit runs (optionally separated by spaces/dashes) look like card PANs.
_PAN_RE = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


def mask_card_numbers(text: str) -> str:
    """Redact full card numbers before the text leaves the bank (keeps last 4)."""

    def _mask(m: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        return f"[CARD ****{digits[-4:]}]"

    return _PAN_RE.sub(_mask, text)


def route(message: InboundMessage, triage: TriageResult) -> RoutingDecision:
    overrides: list[str] = []
    priority = triage.priority

    # A fraud signal anywhere in the message outranks the primary category.
    category = triage.category
    if (
        category != Category.FRAUD_SECURITY
        and Category.FRAUD_SECURITY in triage.secondary_categories
    ):
        overrides.append(f"escalated_from_{category.value}_due_to_secondary_fraud_signal")
        category = Category.FRAUD_SECURITY

    if priority not in PRIORITY_BANDS[category]:
        new_priority = DEFAULT_PRIORITY[category]
        overrides.append(f"priority_{priority.value}_to_{new_priority.value}_per_policy")
        priority = new_priority

    queue = QUEUES[category]
    # Fraud is never parked in manual review: it goes straight to fraud-ops.
    if category != Category.FRAUD_SECURITY and (
        triage.requires_human_review or triage.confidence == Confidence.LOW
    ):
        overrides.append("sent_to_manual_review")
        queue = MANUAL_REVIEW_QUEUE

    for override in overrides:
        logger.debug("[%s] routing override: %s", message.message_id, override)
    logger.info("[%s] routed to %s priority=%s sla=%dm", message.message_id, queue,
                priority.value, SLA_MINUTES[priority])
    return RoutingDecision(
        message_id=message.message_id,
        channel=message.channel,
        queue=queue,
        priority=priority,
        sla_minutes=SLA_MINUTES[priority],
        overrides_applied=overrides,
        triage=triage,
    )
