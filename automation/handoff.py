from uuid import uuid4

from playwright.sync_api import Page

from automation.evidence import EvidenceLogger
from automation.surface import PlaywrightSurface


class HandoffController:
    def __init__(
        self,
        page: Page,
        surface: PlaywrightSurface,
        evidence: EvidenceLogger,
    ):
        self.page = page
        self.surface = surface
        self.evidence = evidence
        self.owner = "automation"
        self.session_id = uuid4().hex[:12]

    def request(
        self,
        reason: str,
        step_index: int,
        operator_instruction: str,
    ) -> None:
        if self.owner != "automation":
            raise RuntimeError(
                "Automation does not currently own the session"
            )

        before = self.surface.safe_snapshot()
        self.owner = "human"

        self.evidence.event(
            "handoff_requested",
            session_id=self.session_id,
            owner=self.owner,
            step_index=step_index,
            reason=reason,
            state=before,
        )

        print()
        print("=== HUMAN HANDOFF ===")
        print(f"Reason: {reason}")
        print(operator_instruction)
        print(
            "Use the browser window that is already open."
        )
        input(
            "After completing the instruction, "
            "press Enter here to return control: "
        )

        # Give Playwright a moment to process browser events
        # that occurred while the terminal was waiting.
        self.page.wait_for_timeout(250)

        after = self.surface.safe_snapshot()

        self.evidence.event(
            "human_action_summary",
            session_id=self.session_id,
            owner="human",
            step_index=step_index,
            before=before,
            after=after,
        )

        self.owner = "automation"

        self.evidence.event(
            "handoff_resumed",
            session_id=self.session_id,
            owner=self.owner,
            step_index=step_index,
            state=after,
        )