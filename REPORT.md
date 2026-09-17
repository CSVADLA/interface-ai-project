# Computer-Use Automation System Report

## Architecture

The system separates probabilistic workflow discovery from deterministic execution.

During discovery, an Ollama-hosted language model observes a structured description of the current browser surface and chooses one action from a runtime-generated allowlist. The decision is parsed and validated with Pydantic before the browser performs it. After the workflow succeeds, the system converts the observed actions into a reusable capability artifact.

During replay, the system loads and validates that artifact and executes it through Playwright without calling the language model.

```text
Goal and inputs
      |
      v
Discovery controller
      |
      +-- observe live Playwright page
      +-- calculate permitted actions
      +-- request structured Ollama decision
      +-- validate decision
      +-- execute approved action
      |
      v
Typed capability artifact
      |
      v
Deterministic replay controller
      |
      +-- validate artifact and workflow order
      +-- execute exact recorded steps
      +-- verify checkpoint
      +-- extract typed output
      |
      v
Structured result and redacted evidence
```

The local Flask application provides a controlled credit-union administration surface using synthetic data. Its workflow is:

1. Enter a member ID.
2. Search for the member.
3. distinguish between a matching member and a member-not-found outcome.
4. Open the member record.
5. Open savings details.
6. Verify the savings page.
7. Extract and validate the savings balance.

`PlaywrightSurface` is the boundary between the controllers and the browser. It exposes narrow operations such as filling an approved field, clicking an approved role and accessible name, waiting for a search outcome, verifying a heading, extracting approved text, observing the current state, and creating a safe structural snapshot.

The discovery and replay controllers depend on this surface rather than using arbitrary Playwright calls. This keeps browser access consistent and makes policy checks part of the execution boundary.

Ollama provides the genuine LLM component. The demonstrated model is `qwen3:4b-instruct`. Ollama is used only during discovery. Replay has no model client and remains functional when Ollama is unavailable.

## Artifact schema

The capability artifact is defined with Pydantic and uses schema version `1.0`. Unknown fields are rejected so accidental or malicious additions cannot silently change execution behavior.

The artifact records:

- Schema version
- Capability name
- Input contract
- Output contract
- Ordered browser steps
- Success checkpoint
- Approved extraction target and format
- Output currency

The supported step types are intentionally small:

- `fill`
- `click`
- `check_search_outcome`

Targets use semantic browser information such as an accessible role, accessible name, or form label. The artifact does not store screen coordinates.

The discovered workflow contains the following ordered operations:

1. Fill **Member ID** from the runtime input.
2. Click **Search**.
3. Check whether the member was found.
4. Click **Open member**.
5. Click **View savings**.
6. Verify the **Savings details** heading.
7. Read the **Savings balance** value.

Runtime inputs remain parameters. The artifact does not contain the discovery member ID or its discovered balance. This was verified by searching the saved artifact for both values and finding neither. The same artifact was subsequently replayed for a different member and returned that member’s balance.

The artifact has two layers of validation. Pydantic validates its types and structure. The policy module then validates the allowed operations, targets, checkpoint, extraction target, and complete step order. A structurally valid artifact cannot reorder or omit required steps and still pass the workflow policy.

## Determinism & error handling

Discovery is probabilistic because a language model selects actions. Replay is deterministic because it performs the saved ordered steps without consulting a model.

Before replay starts, the system validates:

- Artifact structure
- Schema version
- Allowed action types
- Allowed targets
- Required workflow order
- Checkpoint
- Extraction target
- Runtime input format

The replay engine returns typed outcomes rather than using raw exceptions as its public interface.

Supported results include:

- `success` with validated outputs
- `business_outcome` when a member is not found
- `failure` with a recoverable category for a UI timeout
- `failure` with a hard category for an invalid artifact or unexpected condition
- `human_required` when discovery cannot proceed safely

Failures include a code, step index where applicable, expected state, and observed state. This makes failures useful to operators and downstream systems without exposing a Python traceback as the result contract.

The project demonstrates several exceptional paths:

- An unknown member produces `member_not_found`.
- A delayed search result produces recoverable `ui_timeout`.
- An incomplete or reordered artifact produces a hard artifact-flow failure.
- A disallowed URL or action produces a policy violation.
- An unsafe model decision produces human escalation.
- Discovery that exceeds its bounded step count produces human escalation.

Playwright assertion failures are normalized at the surface boundary. For example, a visibility assertion that times out becomes a Playwright timeout understood by the replay controller. This prevents differences between Playwright assertion and action exceptions from leaking through the result contract.

Every run receives a unique run identifier and writes timestamped JSONL events. A failed replay can also produce a safe snapshot containing the current page title, approved headings, and approved controls.

## Heterogeneity & multi-tenant

The current implementation supports one deliberately narrow browser workflow, but its boundaries allow the design to grow.

Surface-specific behavior is isolated in the Playwright adapter. A different website would provide another constrained adapter or another set of approved surface operations while keeping the discovery, artifact, replay, result, and evidence concepts.

The artifact schema can evolve through its explicit version field. A production registry could select a parser and executor by capability name and schema version. New versions could be introduced without silently changing the meaning of existing artifacts.

For multiple tenants, artifacts should be stored by tenant, application, capability name, and version. Runtime credentials and member data should remain outside the artifact. A tenant policy would specify:

- Allowed origins
- Allowed routes
- Approved actions and targets
- Input and output contracts
- Redaction rules
- Artifact versions
- Handoff rules
- Evidence retention

A production implementation should create an isolated browser context for each run and bind it to the tenant’s authenticated session. Tenant identity should also be included in authorization checks and evidence metadata, while sensitive credentials remain in a secret store.

The current artifact is portable across synthetic members because it stores workflow structure and parameter references rather than concrete discovery values.

## Escalation & handoff

The system supports an explicit human handoff during deterministic replay.

The demonstration pauses at the approved **Open member** step. The operator receives a specific instruction and interacts with the browser window that Playwright already opened. The browser process, browser context, page, cookies, navigation history, and application state remain live.

After the operator clicks **Open member**, they return to the terminal and press Enter. Automation verifies that the **Member details** heading is present, resumes ownership, clicks **View savings**, verifies the final checkpoint, and extracts the result.

The evidence contains three linked events:

1. `handoff_requested`
2. `human_action_summary`
3. `handoff_resumed`

These events share one handoff session identifier. The owner changes to `human` during the pause and returns to `automation` when replay resumes.

The action summary records safe before-and-after surface structure. In the demonstrated run, the page changed from an **Open member** control to a **Member details** heading and **View savings** control. It does not record the member identifier or account balance.

Discovery can also return `human_required` when:

- The model requests help.
- The model selects an unavailable or unsafe action.
- The maximum discovery step count is reached.

The demonstration uses a terminal pause as the operator interface. In production, the same ownership protocol could connect to an operator queue and browser-streaming interface.

## Safety

Safety is enforced in code rather than left to the language model.

The navigation policy permits only the local HTTP origin:

```text
http://127.0.0.1:5000
```

It also validates approved routes, query parameters, and the five-digit member ID format. External origins, unknown routes, fragments, and unexpected query parameters are rejected.

The action policy permits only known operations and semantic targets required by the workflow. The LLM receives a narrowed list of actions available in the current state. Its structured response is validated against that list before execution.

The deterministic artifact receives both per-action validation and full-flow validation. This prevents an artifact from containing an individually allowed action in a dangerous or incomplete sequence.

Additional controls include:

- HTTP GET-only mock workflow
- Blocked service workers in the Playwright context
- Bounded discovery steps
- Bounded browser waits
- Exact accessible-name matching
- Typed runtime inputs
- Decimal output validation
- Synthetic application data
- No credentials in the artifact
- No member-specific values in the artifact
- Redacted member identifiers in evidence
- Redacted savings balances in evidence
- Structural failure snapshots instead of unrestricted page content
- Human escalation for unapproved model behavior

The raw model response is not treated as authority. The runtime policy remains the authority for what can be executed.

## Cuts

The implementation is intentionally small and explainable. It demonstrates one complete vertical slice rather than a general browser agent.

The following features were deliberately excluded:

- Production authentication and credential storage
- Live financial systems or real customer data
- Arbitrary websites and unrestricted navigation
- Coordinate-based clicking
- Screenshot or vision-model perception
- Multiple browser engines
- Distributed workers
- Remote operator streaming
- Persistent capability registry
- Automatic artifact migration
- Retry and backoff orchestration
- Long-lived session recovery
- Permission-request UI simulation
- Production monitoring and alerting
- Model comparison and evaluation infrastructure

The mock application, semantic Playwright adapter, local Ollama model, versioned artifact, deterministic replay engine, structured failures, policy enforcement, redacted evidence, and same-session human handoff form the smallest system that demonstrates the required architecture clearly.
