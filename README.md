# Computer-Use Automation System

A small end-to-end computer-use automation system built for the interface.ai take-home assignment.

The system uses an LLM once to discover a workflow against a live browser UI. It records the successful workflow as a typed, versioned capability artifact. Later executions replay that artifact deterministically without calling the LLM.

The demonstration workflow retrieves a synthetic credit-union member’s savings balance.

## System flow

```text
Natural-language goal
        |
        v
LLM discovery loop
Observe -> Decide -> Validate -> Act
        |
        v
Versioned capability artifact
        |
        v
Deterministic replay without LLM
        |
        +-- Success
        +-- Business outcome
        +-- Recoverable failure
        +-- Hard failure
        +-- Human handoff
        |
        v
Redacted evidence
```

## Features

- Local Flask credit-union administration UI
- Playwright browser surface adapter
- Ollama-powered observe-decide-act discovery loop
- Structured LLM output validated with Pydantic
- Typed and versioned capability artifact
- Deterministic replay without an LLM
- Structured success, business, recoverable, and hard outcomes
- Action and navigation allowlists
- Evidence redaction
- JSONL event logs and safe UI snapshots
- Human handoff in the same live browser session
- Unit and browser integration tests

## Project structure

```text
apps/
  server.py
  templates/
automation/
  capability.py
  discover.py
  discovery_models.py
  evidence.py
  handoff.py
  llm.py
  models.py
  policy.py
  replay.py
  surface.py
evidence/
examples/
tests/
README.md
REPORT.md
requirements.txt
```

## Requirements

- Python 3.11 or newer
- Playwright Chromium
- Ollama for LLM discovery
- The `qwen3:4b-instruct` Ollama model

Ollama is required only for discovery. Deterministic replay does not use an LLM.

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies and the Playwright browser:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Install Ollama, then download the local model:

```powershell
ollama pull qwen3:4b-instruct
```

## Start the mock application

Open one terminal, activate the virtual environment, and run:

```powershell
$env:MOCK_SEARCH_DELAY_MS = "0"
python -m flask --app apps.server run --port 5000
```

The application is available at:

```text
http://127.0.0.1:5000
```

All member information in the application is synthetic.

## Run LLM discovery

Keep the Flask application running. In another terminal, run:

```powershell
$env:OLLAMA_MODEL = "qwen3:4b-instruct"
python -m automation.discover --member-id 12345
```

A successful discovery writes the reusable artifact to:

```text
evidence/savings.discovered.json
```

It also creates a run directory under `evidence/runs/` containing the redacted discovery events and the run-specific artifact.

The discovery loop uses Ollama to choose from currently permitted actions. Every decision is validated against a typed schema and the runtime safety policy before execution.

## Run deterministic replay

Replay the discovered capability without calling Ollama:

```powershell
python -m automation.replay `
  --artifact evidence/savings.discovered.json `
  --member-id 67890
```

Using a different member demonstrates that the artifact contains workflow structure rather than discovery-time member data.

Expected output:

```json
{
  "status": "success",
  "code": "completed",
  "outputs": {
    "savings_balance": "875.25",
    "currency": "USD"
  }
}
```

## Demonstrate a business outcome

Use an unknown synthetic member:

```powershell
python -m automation.replay `
  --artifact evidence/savings.discovered.json `
  --member-id 99999
```

Expected result:

```json
{
  "status": "business_outcome",
  "code": "member_not_found",
  "outputs": null
}
```

## Demonstrate human handoff

Run replay with a handoff at the approved Open member step:

```powershell
python -m automation.replay `
  --artifact evidence/savings.discovered.json `
  --member-id 12345 `
  --human-at-step 3
```

When prompted:

1. Use the browser window that is already open.
2. Click **Open member**.
3. Return to the terminal and press Enter.

Automation resumes in the same Playwright page and browser context, verifies the resulting state, and completes the remaining workflow.

The evidence log records:

- `handoff_requested`
- `human_action_summary`
- `handoff_resumed`

All three events use the same handoff session identifier.

## Demonstrate a recoverable timeout

Stop the normal Flask server. Start it again with a delayed search result:

```powershell
$env:MOCK_SEARCH_DELAY_MS = "7000"
python -m flask --app apps.server run --port 5000
```

Then run the normal discovered artifact:

```powershell
python -m automation.replay `
  --artifact evidence/savings.discovered.json `
  --member-id 12345
```

The replay returns a structured recoverable `ui_timeout` failure and writes a safe failure-surface snapshot.

Restore normal behavior afterward:

```powershell
$env:MOCK_SEARCH_DELAY_MS = "0"
```

## Tests

Run the unit test suite:

```powershell
python -m pytest -q
```

Run live browser integration tests while the Flask application is running on port 5000:

```powershell
python -m pytest -q -m integration
```

The integration test confirms that an attempted external navigation is blocked by policy.

## Safety

The system applies safety controls before and during browser execution:

- Only `http://127.0.0.1:5000` is permitted.
- Only known application routes and query parameters are permitted.
- Only approved UI actions and targets are permitted.
- Capability steps must match the complete approved workflow.
- Browser service workers are blocked.
- Unexpected model actions cause human escalation.
- Member identifiers and balances are redacted from event logs.
- Failure evidence contains only approved structural UI information.
- The mock application uses synthetic data.

## Evidence

Each run creates a directory under:

```text
evidence/runs/<run-id>/
```

Depending on the outcome, it can contain:

- `events.jsonl` — structured redacted events
- `capability.json` — the discovered capability
- `failure-surface.json` — safe structural failure evidence

The main discovered artifact is:

```text
evidence/savings.discovered.json
```

The LLM is used during discovery only. Loading and replaying the saved artifact require no model call.

## Design scope

This project intentionally demonstrates one small vertical slice. It focuses on the boundary between probabilistic discovery and deterministic execution rather than providing a general-purpose browser automation platform.

See `REPORT.md` for architectural decisions, determinism, safety, handoff behavior, multi-tenant considerations, and deliberate scope cuts.
