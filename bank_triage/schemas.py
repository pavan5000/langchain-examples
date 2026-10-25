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
    # Filled in by the fraud agent for messages routed to the fraud queue.
    fraud_analysis: FraudAnalysis | None = None


# --------------------------------------------------------------------------- #
# Fraud analysis (second-stage agent, fraud-ops queue only)
# --------------------------------------------------------------------------- #
class FraudType(str, Enum):
    ACCOUNT_TAKEOVER = "account_takeover"
    CARD_NOT_PRESENT = "card_not_present"
    LOST_STOLEN_CARD = "lost_stolen_card"
    CARD_SKIMMING_COUNTERFEIT = "card_skimming_counterfeit"
    PHISHING_SOCIAL_ENGINEERING = "phishing_social_engineering"
    AUTHORIZED_PUSH_PAYMENT_SCAM = "authorized_push_payment_scam"
    IDENTITY_THEFT = "identity_theft"
    SIM_SWAP = "sim_swap"
    ELDER_FINANCIAL_ABUSE = "elder_financial_abuse"
    FRIENDLY_FRAUD = "friendly_fraud"
    UNDETERMINED = "undetermined"


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionOwner(str, Enum):
    FRAUD_OPS = "fraud_ops"
    CARD_SERVICES = "card_services"
    DIGITAL_BANKING = "digital_banking"
    CYBER_SECURITY = "cyber_security"
    FINANCIAL_CRIMES = "financial_crimes"
    CUSTOMER = "customer"


class Timeframe(str, Enum):
    IMMEDIATE = "immediate"
    WITHIN_1_HOUR = "within_1_hour"
    WITHIN_24_HOURS = "within_24_hours"


class FixScope(str, Enum):
    CUSTOMER_ACCOUNT = "customer_account"
    BANK_CONTROL = "bank_control"
    PRODUCT_OR_PROCESS = "product_or_process"


class TacticalAction(OpenAIStrictModel):
    """A containment step that stops the loss now."""

    action: str = Field(description="Concrete step, e.g. 'Block card ending 0366'.")
    owner: ActionOwner
    timeframe: Timeframe
    rationale: str = Field(description="Why this step, tied to the evidence.")


class PermanentFix(OpenAIStrictModel):
    """A remediation that removes the root cause so this can't recur."""

    fix: str = Field(description="Concrete remediation, e.g. 'Enforce phishing-resistant MFA'.")
    owner: ActionOwner
    scope: FixScope
    root_cause_addressed: str = Field(description="The weakness this fix closes.")


class FraudAnalysis(OpenAIStrictModel):
    """Fraud analyst's assessment of one fraud_security case."""

    fraud_type: FraudType = Field(description="Most likely fraud typology.")
    secondary_fraud_types: list[FraudType] = Field(
        description="Other typologies that may also be in play (e.g. phishing leading to ATO)."
    )
    attack_vector: str = Field(
        description="How the fraudster most likely got access, in one or two sentences."
    )
    evidence: list[str] = Field(
        description="Facts from the message and tool results that support the typology."
    )
    estimated_exposure: str | None = Field(
        description="Amount at risk or already lost with currency, or null if unknown."
    )
    risk_level: RiskLevel
    confidence: Confidence
    tactical_actions: list[TacticalAction] = Field(
        description="Containment steps in the order they should happen."
    )
    permanent_fixes: list[PermanentFix] = Field(
        description="Root-cause remediations for the account and, where relevant, the bank."
    )
    customer_guidance: list[str] = Field(
        description="Plain-language steps the analyst should tell the customer to take."
    )
    escalate_to_financial_crimes: bool = Field(
        description="True for organised/repeat patterns, large exposure, or SAR-worthy activity."
    )
    regulatory_considerations: list[str] = Field(
        description="Dispute/chargeback deadlines, SAR filing, vulnerable-customer duties, etc."
    )
    analyst_summary: str = Field(description="Two or three sentences for the case file.")


RoutingDecision.model_rebuild()
