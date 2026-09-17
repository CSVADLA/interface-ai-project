import argparse
import sys
from pathlib import Path
from automation.policy import ArtifactFlowError
from automation.handoff import HandoffController

from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)
from pydantic import ValidationError

from automation.capability import (
    ClickStep,
    FillStep,
    SavingsCapability,
    SearchOutcomeStep,
)
from automation.evidence import EvidenceLogger
from automation.models import (
    BusinessOutcome,
    HardFailure,
    RecoverableFailure,
    SavingsInput,
    SavingsOutput,
    SuccessResult,
)
from automation.policy import (
    PolicyViolation,
    validate_capability,
    validate_flow
)
from automation.surface import PlaywrightSurface


ReplayResult = (
    SuccessResult
    | BusinessOutcome
    | RecoverableFailure
    | HardFailure
)


def replay(
    capability: SavingsCapability,
    inputs: SavingsInput,
    evidence: EvidenceLogger,
    human_at_step: int | None = None
) -> ReplayResult:
    # Validate every recorded action before opening the browser.
    validate_capability(capability)
    validate_flow(capability)

    evidence.event(
        "capability_validated",
        capability=capability.name,
        schema_version=capability.schema_version,
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
            slow_mo=400,
        )

        try:
            context = browser.new_context(
                service_workers="block",
            )
            page = context.new_page()
            page.set_default_timeout(5000)

            surface = PlaywrightSurface(page)
            handoff = HandoffController(
                page=page,
                surface=surface,
                evidence=evidence,
            )

            try:
                surface.navigate(
                    "http://127.0.0.1:5000"
                    + capability.entry_path
                )

                evidence.event(
                    "navigation_completed"
                )

            except PlaywrightTimeoutError:
                return RecoverableFailure(
                    expected="Load capability entry page",
                    observed="Timed out waiting for UI",
                )

            except PolicyViolation:
                return HardFailure(
                    code="policy_violation",
                    expected="Policy-approved entry page",
                    observed="Navigation blocked by policy",
                )

            for step_index, step in enumerate(
                capability.steps
            ):
                evidence.event(
                    "step_started",
                    step_index=step_index,
                    action=step.action,
                )

                try:
                    if human_at_step == step_index:
                        is_open_member_step = (
                            isinstance(step, ClickStep)
                            and step.target.role =="link"
                            and step.target.name  == "Open member"
                        )

                        if not is_open_member_step:
                            return HardFailure(
                                code="unexpexted_error",
                                step_index=step_index,
                                expected=(
                                    "Human handoff at open step"
                                ),
                                observed=(
                                    "Handoff requested at unsupported step"
                                ),
                            )
                        handoff.request(
                            reason=(
                                "Operator review required before "
                                "opening the member record"
                            ),
                            step_index=step_index,
                            operator_instruction=(
                                "Click open member in browser."
                            ),
                        )

                        surface.verify_heading(
                            "Member details"
                        )

                        evidence.event(
                            "step_completed",
                            step_index=step_index,
                            action=step.action,
                            executor="human",
                        )

                        continue

                    if isinstance(step, FillStep):
                        value = getattr(
                            inputs,
                            step.input_parameter,
                        )

                        surface.fill(
                            step.target.name,
                            value,
                        )

                    elif isinstance(step, ClickStep):
                        surface.click(
                            step.target.role,
                            step.target.name,
                        )

                    elif isinstance(
                        step,
                        SearchOutcomeStep,
                    ):
                        outcome = (
                            surface.wait_for_search_outcome()
                        )

                        if outcome == "not_found":
                            evidence.event(
                                "step_completed",
                                step_index=step_index,
                                action=step.action,
                            )

                            return BusinessOutcome(
                                code="member_not_found"
                            )

                    else:
                        evidence.event(
                            "step_failed",
                            step_index=step_index,
                            action=step.action,
                            code="unexpected_error",
                        )

                        return HardFailure(
                            code="unexpected_error",
                            step_index=step_index,
                            expected="Supported replay step",
                            observed="Unsupported step type",
                        )

                    evidence.event(
                        "step_completed",
                        step_index=step_index,
                        action=step.action,
                    )

                except PlaywrightTimeoutError:
                    evidence.event(
                        "step_failed",
                        step_index=step_index,
                        action=step.action,
                        code="ui_timeout",
                    )

                    evidence.snapshot(
                        "failure-surface",
                        surface.safe_snapshot(),
                        )

                    return RecoverableFailure(
                        step_index=step_index,
                        expected=(
                            f"Complete {step.action} step"
                        ),
                        observed="Timed out waiting for UI",
                    )

                except PolicyViolation:
                    evidence.event(
                        "step_failed",
                        step_index=step_index,
                        action=step.action,
                        code="policy_violation",
                    )

                    return HardFailure(
                        code="policy_violation",
                        step_index=step_index,
                        expected="Policy-approved operation",
                        observed="Operation blocked by policy",
                    )

            verification_index = len(
                capability.steps
            )

            try:
                surface.verify_heading(
                    capability.checkpoint.name
                )

                balance_text = surface.read(
                    capability.extraction.target.name
                )

                result = SuccessResult(
                    outputs=SavingsOutput(
                        savings_balance=balance_text,
                        currency=capability.currency,
                    )
                )

                evidence.event(
                    "checkpoint_verified",
                    checkpoint=(
                        capability.checkpoint.name
                    ),
                )

                return result

            except PlaywrightTimeoutError:
                evidence.event(
                    "verification_failed",
                    step_index=verification_index,
                    code="ui_timeout",
                )

                return RecoverableFailure(
                    step_index=verification_index,
                    expected="Savings checkpoint and output",
                    observed="Timed out waiting for UI",
                )

            except PolicyViolation:
                evidence.event(
                    "verification_failed",
                    step_index=verification_index,
                    code="policy_violation",
                )

                return HardFailure(
                    code="policy_violation",
                    step_index=verification_index,
                    expected="Policy-approved verification",
                    observed="Operation blocked by policy",
                )

            except ValidationError:
                evidence.event(
                    "verification_failed",
                    step_index=verification_index,
                    code="invalid_output",
                )

                return HardFailure(
                    code="invalid_output",
                    step_index=verification_index,
                    expected="Decimal savings balance",
                    observed=(
                        "UI returned an invalid output format"
                    ),
                )

        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--human-at-step",
        type=int,
        choices=[3],
        default=None,
        help=(
            "Pause at step 3 so a human performs "
            "the Open member action"
        ),
    )

    parser.add_argument(
        "--artifact",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--member-id",
        required=True,
    )

    args = parser.parse_args()
    evidence = EvidenceLogger(mode="replay")

    try:
        inputs = SavingsInput(
            member_id=args.member_id
        )

    except ValidationError:
        result = BusinessOutcome(
            code="invalid_member_id"
        )

        evidence.event(
            "run_completed",
            result=result.model_dump(),
        )

        print(result.model_dump_json(indent=2))
        print(
            f"Evidence: {evidence.run_directory}",
            file=sys.stderr,
        )
        return

    try:
        artifact_text = args.artifact.read_text(
            encoding="utf-8"
        )

    except OSError:
        evidence.event(
            "artifact_read_failed",
            code="artifact_unreadable",
        )
        parser.error("Could not read the artifact file")

    try:
        capability = SavingsCapability.model_validate_json(
            artifact_text
        )

    except ValidationError:
        evidence.event(
            "artifact_validation_failed",
            code="invalid_artifact",
        )
        parser.error(
            "Artifact does not match capability schema 1.0"
        )

    try:
        result = replay(
            capability,
            inputs,
            evidence,
            human_at_step=args.human_at_step,
        )

    except PolicyViolation:
        result = HardFailure(
            code="policy_violation",
            expected="Policy-approved capability",
            observed="Artifact blocked before execution",
        )

    except ArtifactFlowError:
        result = HardFailure(
            code="unexpected_error",
            expected="Complete approved savings workflow",
            observed="Artifact has missing or reordered steps",
        )

    evidence.event(
        "run_completed",
        result=result.model_dump(),
    )

    print(result.model_dump_json(indent=2))
    print(
        f"Evidence: {evidence.run_directory}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()