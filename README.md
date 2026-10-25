# Omni-Channel Bank Request Triage (LangChain + OpenAI)

Classifies inbound customer messages (email, secure chat, mobile app form), assesses urgency,
extracts entities, and routes each message to an internal queue.

```
message ──► mask card PANs ──► LangChain agent (OpenAI + tools) ──► TriageResult (schema-valid JSON)
                                                                         │
                                       deterministic routing rules ◄─────┘
                                                                         ▼
                                                                 RoutingDecision (queue, priority, SLA)
```

| File | Purpose |
|---|---|
| `bank_triage/schemas.py` | Pydantic models: `InboundMessage`, `TriageResult` (the structured output), `RoutingDecision` |
| `bank_triage/agent.py` | `create_agent` + `ProviderStrategy(TriageResult)`, which uses OpenAI's native structured outputs |
| `bank_triage/tools.py` | `lookup_account_profile`, `get_recent_security_events` (mock data; replace with real services) |
| `bank_triage/routing.py` | Queue map, priority policy, SLAs, manual-review fallback, PAN masking |

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
.venv/bin/python main.py                                  # all sample messages
.venv/bin/python main.py --text "My card was stolen" --channel secure_chat
.venv/bin/python -m pytest -q                             # offline routing tests
```
