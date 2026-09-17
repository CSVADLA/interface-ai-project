# Evidence

This directory contains stable evidence for the demonstrated workflow. Raw timestamped runs remain under `runs/`.

## Files

### `savings.discovered.json`

Versioned capability artifact produced by the Ollama-driven discovery run.

The artifact contains workflow structure and parameter references. It does not contain the member ID or savings balance used during discovery.

### `discovery.events.jsonl`

Events from successful LLM-driven discovery.

Run ID: `20260917T014751Z-6cfa936b`

This log records structured observations and model decisions from Ollama using `qwen3:4b-instruct`.

### `replay.events.jsonl`

Events from deterministic replay of the discovered artifact for a different synthetic member.

Run ID: `20260917T054841Z-1a4d2f9a`

Replay completed successfully with the expected savings output.

No LLM was used during this replay.

### `handoff.events.jsonl`

Events from replay with a human handoff at the Open member step.

Run ID: `20260917T023308Z-685080e1`

The log records:

1. `handoff_requested`
2. `human_action_summary`
3. `handoff_resumed`

The events share a handoff session identifier and demonstrate control moving from automation to a human and back to automation in the same live browser session.

### `timeout.events.jsonl`

Events from a replay in which the mock application delayed the search result beyond the permitted UI wait.

Run ID: `20260916T024107Z-b3c86686`

The replay returned a structured recoverable `ui_timeout` failure.

### `timeout.failure-surface.json`

Safe structural UI snapshot recorded for the timeout failure. It contains approved page structure only and excludes member identifiers and balances.

## Redaction

Evidence logging redacts sensitive runtime values, including:

- Member identifiers
- Savings balances

The mock application contains synthetic data only.
