"""Tools the triage agent may call to enrich its urgency assessment.

These hit an in-memory mock. Swap the bodies for calls to your core-banking /
CRM / fraud-signal services.
"""

from __future__ import annotations

import json
import logging

from langchain.tools import tool

logger = logging.getLogger(__name__)

_ACCOUNTS: dict[str, dict] = {
    "4410023318": {
        "customer_segment": "private_banking",
        "is_vulnerable_customer": False,
        "open_cases": 0,
        "recent_security_events": [
            {"type": "new_device_login", "when": "2026-10-21T23:14Z", "geo": "Lagos, NG"},
            {"type": "password_reset", "when": "2026-10-21T23:16Z"},
        ],
    },
    "7720019845": {
        "customer_segment": "retail",
        "is_vulnerable_customer": True,
        "open_cases": 2,
        "recent_security_events": [],
    },
    "9930011274": {
        "customer_segment": "retail",
        "is_vulnerable_customer": False,
        "open_cases": 0,
        "recent_security_events": [],
    },
}


def _normalize(account_number: str) -> str:
    return "".join(ch for ch in account_number if ch.isdigit())


@tool
def lookup_account_profile(account_number: str) -> str:
    """Look up a customer's account profile by account number.

    Returns the customer segment, whether they are flagged as a vulnerable
    customer, and how many cases are already open. Use this when the message
    contains an account number, to inform urgency.
    """
    acct = _ACCOUNTS.get(_normalize(account_number))
    logger.debug("lookup_account_profile account=***%s found=%s",
                 _normalize(account_number)[-4:], acct is not None)
    if acct is None:
        return json.dumps({"found": False, "account_number": account_number})
    return json.dumps(
        {
            "found": True,
            "customer_segment": acct["customer_segment"],
            "is_vulnerable_customer": acct["is_vulnerable_customer"],
            "open_cases": acct["open_cases"],
        }
    )


@tool
def get_recent_security_events(account_number: str) -> str:
    """Get security events (new-device logins, password resets, card blocks)
    recorded on an account in the last 72 hours.

    Use this when the message hints at fraud, a compromised login, or a
    lost/stolen card, to confirm whether there is corroborating activity.
    """
    acct = _ACCOUNTS.get(_normalize(account_number))
    logger.debug("get_recent_security_events account=***%s events=%d",
                 _normalize(account_number)[-4:],
                 len(acct["recent_security_events"]) if acct else 0)
    if acct is None:
        return json.dumps({"found": False, "events": []})
    return json.dumps({"found": True, "events": acct["recent_security_events"]})


TRIAGE_TOOLS = [lookup_account_profile, get_recent_security_events]
