"""Run the triage agent over sample messages (or one message from the CLI).

    python main.py                         # all messages in sample_messages.json
    python main.py --text "Lost my card"   # a single ad-hoc message
    python main.py --debug                 # application debug logs (or TRIAGE_DEBUG=1)
    python main.py --langchain-debug       # full LangChain internal trace (very verbose)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from bank_triage import Channel, InboundMessage, TriagePipeline


def configure_logging(debug: bool, langchain_debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Keep third-party HTTP chatter out of the app logs.
    for noisy in ("httpx", "httpcore", "httpx2", "httpcore2", "openai", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    if langchain_debug:
        from langchain_core.globals import set_debug

        set_debug(True)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="sample_messages.json")
    parser.add_argument("--text", help="Triage a single message instead of the file.")
    parser.add_argument("--channel", default="email", choices=[c.value for c in Channel])
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.getenv("TRIAGE_DEBUG", "").lower() in ("1", "true", "yes"),
        help="Show application debug logs (also enabled by TRIAGE_DEBUG=1).",
    )
    parser.add_argument(
        "--langchain-debug",
        action="store_true",
        help="Also print LangChain's full internal trace of every step.",
    )
    args = parser.parse_args()
    configure_logging(args.debug, args.langchain_debug)

    if args.text:
        messages = [InboundMessage(message_id="cli-1", channel=args.channel, body=args.text)]
    else:
        raw = json.loads(Path(args.file).read_text())
        messages = [InboundMessage.model_validate(m) for m in raw]

    pipeline = TriagePipeline()
    for msg in messages:
        decision = pipeline.process(msg)
        t = decision.triage
        print(
            f"\n[{decision.message_id}] -> {decision.queue} "
            f"| {decision.priority.value.upper()} (SLA {decision.sla_minutes}m) "
            f"| {t.category.value}/{t.sub_intent} | confidence={t.confidence.value}"
        )
        if decision.overrides_applied:
            print(f"  overrides: {', '.join(decision.overrides_applied)}")
        if fa := decision.fraud_analysis:
            print(f"  fraud: {fa.fraud_type.value} | risk={fa.risk_level.value} "
                  f"| escalate_to_financial_crimes={fa.escalate_to_financial_crimes}")
            print("  tactical:")
            for a in fa.tactical_actions:
                print(f"    - [{a.timeframe.value}] {a.action} ({a.owner.value})")
            print("  permanent:")
            for f in fa.permanent_fixes:
                print(f"    - [{f.scope.value}] {f.fix} ({f.owner.value})")
        print(json.dumps(decision.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
