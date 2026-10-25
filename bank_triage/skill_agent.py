"""Shared builder for skill-driven Deep Agents.

Each stage's instructions live in `skills/<skill_set>/<skill>/SKILL.md`, plus
the reference files it points to. The agent sees its skill catalog in the
system prompt, reads the SKILL.md with `read_file`, and pulls in references
only when the case calls for them (progressive disclosure).

The agents process untrusted customer text, so file access is read-only and
confined to the agent's own skill set, and the shell, file-writing and
subagent tools are disabled.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from deepagents import (
    FilesystemPermission,
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile,
)
from deepagents.backends import FilesystemBackend
from langchain.agents.structured_output import ProviderStrategy
from langchain_openai import ChatOpenAI

from .routing import mask_card_numbers
from .schemas import InboundMessage

MODEL = os.getenv("TRIAGE_MODEL", "gpt-6.1-sol")
SKILLS_DIR = Path(os.getenv("TRIAGE_SKILLS_DIR", Path(__file__).resolve().parent.parent / "skills"))

# Read-only harness: keep ls / read_file / glob / grep, drop everything that
# writes, executes, or spawns subagents.
register_harness_profile(
    f"openai:{MODEL}",
    HarnessProfile(
        excluded_tools=frozenset({"write_file", "edit_file", "delete", "execute"}),
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ),
)
_DENY_WRITES = [FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")]


def build_model(reasoning_effort: str = "low", max_tokens: int = 4096) -> ChatOpenAI:
    return ChatOpenAI(model=MODEL, reasoning_effort=reasoning_effort, max_tokens=max_tokens)


def build_skill_agent(
    *,
    skill_set: str,
    skill: str,
    tools: list,
    response_schema: type,
    reasoning_effort: str,
    max_tokens: int,
):
    """Build a Deep Agent that must follow `skills/<skill_set>/<skill>/SKILL.md`.

    Each agent's filesystem is rooted at its own skill set, so it only sees
    (and can only read) the skills meant for its stage.
    """
    system_prompt = (
        "You are an operations agent at a retail bank. For every case, first "
        f"read /{skill}/SKILL.md with read_file and follow it. Read the "
        "reference files it points to when the case calls for them. Your final "
        "answer is the structured result the skill describes."
    )
    return create_deep_agent(
        model=build_model(reasoning_effort, max_tokens),
        tools=tools,
        system_prompt=system_prompt,
        skills=[("/", "Bank operations")],
        backend=FilesystemBackend(root_dir=SKILLS_DIR / skill_set, virtual_mode=True),
        permissions=_DENY_WRITES,
        # Native structured outputs (OpenAI json_schema, strict).
        response_format=ProviderStrategy(response_schema, strict=True),
        name=skill,
    )


def format_message(message: InboundMessage) -> str:
    parts = [f"Channel: {message.channel.value}"]
    if message.customer_id:
        parts.append(f"Customer ID: {message.customer_id}")
    if message.subject:
        parts.append(f"Subject: {mask_card_numbers(message.subject)}")
    parts.append(f"<customer_message>\n{mask_card_numbers(message.body)}\n</customer_message>")
    return "\n".join(parts)


def log_agent_steps(log: logging.Logger, message_id: str, messages: list[Any]) -> None:
    """Log each skill file read, tool call, tool result and model turn."""
    input_tokens = output_tokens = 0
    for msg in messages:
        if msg.type == "ai":
            for call in msg.tool_calls:
                if call["name"] == "read_file":
                    log.debug("[%s] skill read -> %s", message_id,
                              call["args"].get("file_path") or call["args"])
                else:
                    log.debug("[%s] tool call -> %s(%s)", message_id, call["name"],
                              call["args"])
            usage = msg.usage_metadata or {}
            input_tokens += usage.get("input_tokens", 0)
            output_tokens += usage.get("output_tokens", 0)
        elif msg.type == "tool" and msg.name != "read_file":
            log.debug("[%s] tool result <- %s: %s", message_id, msg.name, msg.content)
    model_turns = sum(1 for m in messages if m.type == "ai")
    log.debug("[%s] model turns=%d tokens in=%d out=%d", message_id, model_turns,
              input_tokens, output_tokens)
