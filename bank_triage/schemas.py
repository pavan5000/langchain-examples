"""Pydantic schemas: what comes in, what the LLM must return, and what gets routed."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from pydantic.json_schema import DEFAULT_REF_TEMPLATE, GenerateJsonSchema, JsonSchemaMode


class Channel(str, Enum):
    EMAIL = "email"
    SECURE_CHAT = "secure_chat"
    MOBILE_APP_FORM = "mobile_app_form"


class Category(str, Enum):
    FRAUD_SECURITY = "fraud_security"
    ACCOUNT_SERVICES = "account_services"
    LENDING_MORTGAGES = "lending_mortgages"
    GENERAL_INQUIRY = "general_inquiry"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Sentiment(str, Enum):
    DISTRESSED = "distressed"
    FRUSTRATED = "frustrated"
    NEUTRAL = "neutral"
    POSITIVE = "positive"


class CardType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    PREPAID = "prepaid"
    BUSINESS = "business"


# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #
class InboundMessage(BaseModel):
    message_id: str
    channel: Channel
    body: str
    subject: str | None = None
    customer_id: str | None = None


# --------------------------------------------------------------------------- #
# Structured output the agent must produce
# --------------------------------------------------------------------------- #
class OpenAIStrictJsonSchema(GenerateJsonSchema):
    """JSON schema that OpenAI strict structured outputs accepts.

    Strict mode rejects a `$ref` with sibling keywords (Pydantic emits
    `{"$ref": ..., "description": ...}` for described enum fields) and doesn't
    support `default`. Inline such refs and drop defaults; Python-side
    defaults are unaffected.
    """

    def generate(self, schema, mode="validation"):
        json_schema = super().generate(schema, mode=mode)
        defs = json_schema.get("$defs", {})

        def fix(node: Any) -> Any:
            if isinstance(node, list):
                return [fix(n) for n in node]
            if not isinstance(node, dict):
                return node
            node = {k: fix(v) for k, v in node.items() if k != "default"}
            ref = node.get("$ref")
            if ref and len(node) > 1:
                target = defs[ref.split("/")[-1]]
                node = {**fix(target), **{k: v for k, v in node.items() if k != "$ref"}}
            return node

        return fix(json_schema)


class OpenAIStrictModel(BaseModel):
    @classmethod
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = OpenAIStrictJsonSchema,
        mode: JsonSchemaMode = "validation",
        **kwargs: Any,
    ) -> dict[str, Any]:
        return super().model_json_schema(
            by_alias=by_alias,
            ref_template=ref_template,
            schema_generator=schema_generator,
            mode=mode,
            **kwargs,
        )


class ExtractedEntities(OpenAIStrictModel):
    """Key entities found in the message. Leave lists empty / fields null if absent."""

    account_numbers: list[str] = Field(
        default_factory=list,
        description="Bank account numbers mentioned, exactly as written (may be masked).",
    )
    card_type: CardType | None = Field(
        default=None,
        description="Type of card referenced, if any.",
    )
    card_last_four: str | None = Field(
        default=None,
        description="Last four digits of a card, if mentioned.",
    )
    amounts: list[str] = Field(
        default_factory=list,
        description="Monetary amounts with currency, e.g. '$1,249.00'.",
    )
    merchants: list[str] = Field(
        default_factory=list, description="Merchant names tied to disputed/unknown charges."
    )
    dates: list[str] = Field(
        default_factory=list,
        description="Dates or relative times mentioned, e.g. '2026-10-20' or 'last night'.",
    )
    loan_or_mortgage_reference: str | None = Field(
        default=None,
        description="Loan / mortgage / application reference number.",
    )
    location: str | None = Field(
        default=None,
        description="Branch, city, or address mentioned.",
    )


class TriageResult(OpenAIStrictModel):
    """Classification of one customer message."""

    category: Category = Field(description="Primary department this request belongs to.")
    sub_intent: str = Field(
        description=(
            "Short snake_case label for the specific need, e.g. 'unauthorized_charge', "
            "'lost_card', 'suspicious_login', 'address_change', 'pin_reset', "
            "'fee_dispute', 'statement_request', 'mortgage_rate_inquiry', "
            "'loan_application', 'payoff_statement', 'branch_hours', 'savings_rate'."
        )
    )
    secondary_categories: list[Category] = Field(
        default_factory=list,
        description="Other categories also present in the message (multi-intent).",
    )
    priority: Priority = Field(description="Urgency assessment.")
    urgency_rationale: str = Field(
        description="One sentence explaining the priority, citing evidence from the message."
    )
    confidence: Confidence = Field(description="Confidence in the category assignment.")
    sentiment: Sentiment
    entities: ExtractedEntities
    summary: str = Field(description="One- or two-sentence neutral summary for the agent desk.")
    requires_human_review: bool = Field(
        description=(
            "True if the message is ambiguous, threatens legal/regulatory action, mentions "
            "vulnerability (e.g. elder abuse, coercion), or otherwise needs a person."
        )
    )


# --------------------------------------------------------------------------- #
# Final routing decision (computed deterministically from TriageResult)
# --------------------------------------------------------------------------- #
class RoutingDecision(BaseModel):
    message_id: str
    channel: Channel
    queue: str
    priority: Priority
    sla_minutes: int
    overrides_applied: list[str]
    triage: TriageResult
