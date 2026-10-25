"""Offline tests for the deterministic routing layer (no API calls)."""

from bank_triage.routing import MANUAL_REVIEW_QUEUE, mask_card_numbers, route
from bank_triage.schemas import (
    Category,
    Channel,
    Confidence,
    ExtractedEntities,
    InboundMessage,
    Priority,
    Sentiment,
    TriageResult,
)

MSG = InboundMessage(message_id="m1", channel=Channel.EMAIL, body="...")


def make(category, priority, *, secondary=(), confidence=Confidence.HIGH, review=False):
    return TriageResult(
        category=category,
        sub_intent="x",
        secondary_categories=list(secondary),
        priority=priority,
        urgency_rationale="r",
        confidence=confidence,
        sentiment=Sentiment.NEUTRAL,
        entities=ExtractedEntities(),
        summary="s",
        requires_human_review=review,
    )


def test_fraud_always_high():
    d = route(MSG, make(Category.FRAUD_SECURITY, Priority.LOW))
    assert d.queue == "fraud-ops"
    assert d.priority == Priority.HIGH
    assert d.sla_minutes == 15


def test_secondary_fraud_escalates():
    d = route(
        MSG,
        make(Category.ACCOUNT_SERVICES, Priority.MEDIUM, secondary=[Category.FRAUD_SECURITY]),
    )
    assert d.queue == "fraud-ops"
    assert d.priority == Priority.HIGH


def test_general_inquiry_capped_low():
    d = route(MSG, make(Category.GENERAL_INQUIRY, Priority.HIGH))
    assert d.queue == "general-inquiries"
    assert d.priority == Priority.LOW


def test_low_confidence_goes_to_manual_review():
    d = route(MSG, make(Category.LENDING_MORTGAGES, Priority.LOW, confidence=Confidence.LOW))
    assert d.queue == MANUAL_REVIEW_QUEUE


def test_fraud_never_parked_in_manual_review():
    d = route(MSG, make(Category.FRAUD_SECURITY, Priority.HIGH, review=True))
    assert d.queue == "fraud-ops"


def test_mask_card_numbers():
    out = mask_card_numbers("card 4532 0151 1283 0366 and acct 4410023318")
    assert out == "card [CARD ****0366] and acct 4410023318"
