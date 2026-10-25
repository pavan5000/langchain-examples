# Omni-Channel Bank Request Triage (LangChain + OpenAI)

Classifies inbound customer messages (email, secure chat, mobile app form), assesses urgency,
extracts entities, and routes each message to an internal queue.

```
message ──► mask card PANs ──► triage Deep Agent (bank-triage skill + tools) ──► TriageResult (schema-valid JSON)
                                                                         │
                                       deterministic routing rules ◄─────┘
                                                                         ▼
                                                                 RoutingDecision (queue, priority, SLA)
                                                                         │ queue == fraud-ops
                                                                         ▼
                                    fraud Deep Agent (fraud-analysis skill + playbooks) ──► FraudAnalysis
```

| File | Purpose |
|---|---|
| `bank_triage/schemas.py` | Pydantic models: `InboundMessage`, `TriageResult` (the structured output), `RoutingDecision` |
| `skills/triage/bank-triage/` | Triage skill: categories, priority policy, tool rules (`SKILL.md`) and sub-intent labels (`references/`) |
| `skills/fraud/fraud-analysis/` | Fraud skill: investigation workflow (`SKILL.md`), one playbook per fraud type (`playbooks/`), escalation and regulatory notes (`references/`) |
| `bank_triage/skill_agent.py` | Builds a read-only Deep Agent for a skill: OpenAI model, skill catalog, strict structured output |
| `bank_triage/classifier_agent.py` | Triage stage: runs the `bank-triage` skill, returns `TriageResult` |
| `bank_triage/fraud_agent.py` | Fraud stage for `fraud-ops` cases: runs the `fraud-analysis` skill, returns `FraudAnalysis` |
| `bank_triage/pipeline.py` | `TriagePipeline`: triage every message, hand fraud cases to the fraud agent |
| `bank_triage/tools.py` | Account profile, security events, transactions tools (mock data; replace with real services) |
| `bank_triage/routing.py` | Queue map, priority policy, SLAs, manual-review fallback, PAN masking |

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
.venv/bin/python main.py                                  # all sample messages
.venv/bin/python main.py --text "My card was stolen" --channel secure_chat
.venv/bin/python -m pytest -q                             # offline routing tests
```

## Editing the behaviour

The agents' instructions are Markdown, not Python. To change a priority rule,
add a sub-intent, or refine a fraud playbook, edit the files under `skills/`;
no code change is needed. Add a new fraud playbook by creating
`skills/fraud/fraud-analysis/playbooks/<name>.md` and listing it in the table
in that skill's `SKILL.md`. Run with `--debug` to see which skill files each
agent read.
