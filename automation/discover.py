import argparse
import sys
from pathlib import Path

from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)
from pydantic import ValidationError

from automation.capability import (
    BalanceExtraction,
    ClickStep,
    FillStep,
    LabelTarget,
    RoleTarget,
    SavingsCapability,
    SearchOutcomeStep,
)
from automation.evidence import EvidenceLogger
from automation.llm import (
    DecisionClient,
    OllamaDecisionClient,
)
from automation.models import (
    BusinessOutcome,
    HardFailure,
    HumanRequired,
    RecoverableFailure,
    SavingsInput,
    SavingsOutput,
    SuccessResult,
)
from automation.policy import (
    PolicyViolation,
    validate_capability,
    validate_flow,
)
from automation.surface import PlaywrightSurface


GOAL = (
    "Read the savings balance for "
    "the supplied member ID"
)

MAX_STEPS = 10

DiscoveryResult = (
    SuccessResult
    | BusinessOutcome
    | RecoverableFailure
    | HardFailure
    | HumanRequired
)


def build_capability(
    steps: list,
) -> SavingsCapability:
    capability = SavingsCapability(
        steps=steps,
        checkpoint=RoleTarget(
            role="heading",
            name="Savings details",
        ),
        extraction=BalanceExtraction(
            target=LabelTarget(
                name="Savings balance"
            ),
        ),
    )

    validate_capability(capability)
    validate_flow(capability)

    return capability


def run_discovery(
    client: DecisionClient,
    inputs: SavingsInput,
    evidence: EvidenceLogger,
    headless: bool = False,
) -> tuple[
    DiscoveryResult,
    SavingsCapability | None,
]:
    recorded_steps = []
    previous_actions = []
    captured_output = None

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=headless,
            slow_mo=400 if not headless else 0,
        )

        try:
            context = browser.new_context(
                service_workers="block",
            )
            page = context.new_page()
            page.set_default_timeout(5000)

            surface = PlaywrightSurface(page)

            try:
                surface.navigate(
                    "http://127.0.0.1:5000/"
                )
            except PlaywrightTimeoutError:
                return (
                    RecoverableFailure(
                        expected="Load discovery entry page",
                        observed="Timed out waiting for UI",
                    ),
                    None,
                )
            except PolicyViolation:
                return (
                    HardFailure(
                        code="policy_violation",
                        expected="Approved discovery entry page",
                        observed="Navigation blocked by policy",
                    ),
                    None,
                )

            for step_index in range(MAX_STEPS):
                observation = surface.observe()

                evidence.event(
                    "observation",
                    step_index=step_index,
                    screen=observation.screen,
                    available_actions=(
                        observation.available_actions
                    ),
                    member_id_entered=(
                        observation.member_id_entered
                    ),
                    search_outcome=(
                        observation.search_outcome
                    ),
                    balance_visible=(
                        observation.balance_visible
                    ),
                )

                try:
                    decision, decision_id = client.decide(
                        goal=GOAL,
                        observation=observation,
                        previous_actions=previous_actions,
                        output_captured=(
                            captured_output is not None
                        ),
                    )
                except Exception:
                    return (
                        HardFailure(
                            code="unexpected_error",
                            step_index=step_index,
                            expected="Valid local-model decision",
                            observed=(
                                "Model decision request failed"
                            ),
                        ),
                        None,
                    )

                evidence.event(
                    "model_decision",
                    step_index=step_index,
                    provider=client.provider,
                    model=client.model,
                    decision_id=decision_id,
                    action=decision.action,
                    reason=decision.reason,
                )

                allowed_now = [
                    action
                    for action in observation.available_actions
                    if action not in previous_actions
                ]

                if (
                    decision.action not in allowed_now
                    and decision.action
                    not in {
                        "finish",
                        "request_handoff",
                    }
                ):
                    return (
                        HumanRequired(
                            code="unsafe_decision",
                            step_index=step_index,
                            reason=(
                                "Model selected an unavailable "
                                "or unsafe action"
                            ),
                        ),
                        None,
                    )

                try:
                    if decision.action == "fill_member_id":
                        surface.fill(
                            "Member ID",
                            inputs.member_id,
                        )

                        recorded_steps.append(
                            FillStep(
                                target=LabelTarget(
                                    name="Member ID"
                                )
                            )
                        )

                    elif decision.action == "click_search":
                        surface.click(
                            "button",
                            "Search",
                        )

                        recorded_steps.append(
                            ClickStep(
                                target=RoleTarget(
                                    role="button",
                                    name="Search",
                                )
                            )
                        )

                    elif (
                        decision.action
                        == "check_search_outcome"
                    ):
                        outcome = (
                            surface.wait_for_search_outcome()
                        )

                        recorded_steps.append(
                            SearchOutcomeStep()
                        )

                        if outcome == "not_found":
                            return (
                                BusinessOutcome(
                                    code="member_not_found"
                                ),
                                None,
                            )

                    elif (
                        decision.action
                        == "click_open_member"
                    ):
                        surface.click(
                            "link",
                            "Open member",
                        )

                        recorded_steps.append(
                            ClickStep(
                                target=RoleTarget(
                                    role="link",
                                    name="Open member",
                                )
                            )
                        )

                    elif (
                        decision.action
                        == "click_view_savings"
                    ):
                        surface.click(
                            "link",
                            "View savings",
                        )

                        recorded_steps.append(
                            ClickStep(
                                target=RoleTarget(
                                    role="link",
                                    name="View savings",
                                )
                            )
                        )

                    elif (
                        decision.action
                        == "read_savings_balance"
                    ):
                        surface.verify_heading(
                            "Savings details"
                        )

                        balance_text = surface.read(
                            "Savings balance"
                        )

                        captured_output = SavingsOutput(
                            savings_balance=balance_text
                        )

                        capability = build_capability(
                            recorded_steps
                        )

                        evidence.event(
                            "goal_verified",
                            step_index=step_index,
                            checkpoint="Savings details",
                            output="savings_balance",
                        )

                        return (
                            SuccessResult(
                                outputs=captured_output
                            ),
                            capability,
                        )

                    elif decision.action == "finish":
                        if captured_output is None:
                            return (
                                HumanRequired(
                                    code="unsafe_decision",
                                    step_index=step_index,
                                    reason=(
                                        "Model tried to finish "
                                        "before capturing output"
                                    ),
                                ),
                                None,
                            )

                        capability = build_capability(
                            recorded_steps
                        )

                        return (
                            SuccessResult(
                                outputs=captured_output
                            ),
                            capability,
                        )

                    elif (
                        decision.action
                        == "request_handoff"
                    ):
                        return (
                            HumanRequired(
                                code="model_requested",
                                step_index=step_index,
                                reason=(
                                    "Model requested human help"
                                ),
                            ),
                            None,
                        )

                    previous_actions.append(
                        decision.action
                    )

                except PlaywrightTimeoutError:
                    evidence.snapshot(
                        "failure-surface",
                        surface.safe_snapshot(),
                    )

                    return (
                        RecoverableFailure(
                            step_index=step_index,
                            expected=(
                                f"Complete "
                                f"{decision.action} action"
                            ),
                            observed=(
                                "Timed out waiting for UI"
                            ),
                        ),
                        None,
                    )

                except PolicyViolation:
                    return (
                        HardFailure(
                            code="policy_violation",
                            step_index=step_index,
                            expected=(
                                "Policy-approved discovery "
                                "operation"
                            ),
                            observed=(
                                "Operation blocked by policy"
                            ),
                        ),
                        None,
                    )

                except ValidationError:
                    return (
                        HardFailure(
                            code="invalid_output",
                            step_index=step_index,
                            expected=(
                                "Valid savings output"
                            ),
                            observed=(
                                "UI returned invalid output"
                            ),
                        ),
                        None,
                    )

            return (
                HumanRequired(
                    code="max_steps",
                    step_index=MAX_STEPS,
                    reason=(
                        "Discovery reached its maximum "
                        "step count"
                    ),
                ),
                None,
            )

        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--member-id",
        required=True,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "evidence/savings.discovered.json"
        ),
    )
    parser.add_argument(
        "--headless",
        action="store_true",
    )

    args = parser.parse_args()
    evidence = EvidenceLogger(mode="discovery")

    try:
        inputs = SavingsInput(
            member_id=args.member_id
        )
    except ValidationError:
        result = BusinessOutcome(
            code="invalid_member_id"
        )
        capability = None
    else:
        client = OllamaDecisionClient()

        result, capability = run_discovery(
            client=client,
            inputs=inputs,
            evidence=evidence,
            headless=args.headless,
        )

    if capability is not None:
        artifact_json = (
            capability.model_dump_json(indent=2)
        )

        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            artifact_json,
            encoding="utf-8",
        )

        (
            evidence.run_directory
            / "capability.json"
        ).write_text(
            artifact_json,
            encoding="utf-8",
        )

        evidence.event(
            "capability_recorded",
            schema_version=(
                capability.schema_version
            ),
            capability=capability.name,
        )

    evidence.event(
        "run_completed",
        result=result.model_dump(),
    )

    print(result.model_dump_json(indent=2))

    if capability is not None:
        print(
            f"Artifact: {args.output}",
            file=sys.stderr,
        )

    print(
        f"Evidence: {evidence.run_directory}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()