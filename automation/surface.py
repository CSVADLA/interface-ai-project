import re
from contextlib import contextmanager
from typing import Literal
from automation.discovery_models import SurfaceObservation
from playwright.sync_api import Page, Route, expect, TimeoutError as PlaywrightTimeoutError

from automation.policy import (
    ALLOWED_CLICKS,
    PolicyViolation,
    validate_url,
)


class PlaywrightSurface:
    def __init__(self, page: Page):
        self.page = page
        self._request_blocked = False

        # Apply the policy to requests across this browser context.
        self.page.context.route("**/*", self._guard_request)

    def _guard_request(self, route: Route) -> None:
        try:
            validate_url(route.request.url)

            if route.request.method != "GET":
                raise PolicyViolation("Request method is not allowed")

        except PolicyViolation:
            self._request_blocked = True
            route.abort()
            return

        route.continue_()

    def safe_snapshot(self) -> dict:
        validate_url(self.page.url)

        headings = self.page.locator(
            "h1, h2"
        ).all_inner_texts()

        controls = self.page.locator(
            "button, a"
        ).all_inner_texts()

        return {
            "title": self.page.title(),
            "headings": [
                text.strip()
                for text in headings
                if text.strip()
            ],
            "controls": [
                text.strip()
                for text in controls
                if text.strip()
            ],
        }

    def observe(self) -> SurfaceObservation:
        validate_url(self.page.url)

        search_heading = self.page.get_by_role(
            "heading",
            name="Credit Union Admin",
            exact=True,
        )
        result_heading = self.page.get_by_role(
            "heading",
            name="Search result",
            exact=True,
        )
        member_heading = self.page.get_by_role(
            "heading",
            name="Member details",
            exact=True,
        )
        savings_heading = self.page.get_by_role(
            "heading",
            name="Savings details",
            exact=True,
        )

        if savings_heading.is_visible():
            screen = "savings_details"
        elif member_heading.is_visible():
            screen = "member_details"
        elif result_heading.is_visible():
            screen = "search_result"
        elif search_heading.is_visible():
            screen = "search"
        else:
            screen = "unknown"

        member_input = self.page.get_by_label(
            "Member ID",
            exact=True,
        )

        member_id_entered = (
            member_input.count() > 0
            and bool(member_input.input_value())
        )

        open_member = self.page.get_by_role(
            "link",
            name="Open member",
            exact=True,
        )
        not_found = self.page.get_by_role("status").filter(
            has_text=re.compile(r"^Member not found\.$")
        )

        if not_found.is_visible():
            search_outcome = "not_found"
        elif open_member.is_visible():
            search_outcome = "found"
        else:
            search_outcome = "none"

        available_actions = []

        if member_input.is_visible():
            available_actions.append("fill_member_id")

        if self.page.get_by_role(
            "button",
            name="Search",
            exact=True,
        ).is_visible():
            available_actions.append("click_search")

        search_button = self.page.get_by_role(
            "button",
            name="Search",
            exact=True,
        )

        if search_button.is_visible():
            available_actions.append(
                "click_search"
            )

        if (
            member_id_entered
            and search_button.is_visible()
        ):
            available_actions.append(
                "check_search_outcome"
            )

        if open_member.is_visible():
            available_actions.append(
                "click_open_member"
            )

        if self.page.get_by_role(
            "link",
            name="View savings",
            exact=True,
        ).is_visible():
            available_actions.append(
                "click_view_savings"
            )

        balance = self.page.get_by_label(
            "Savings balance",
            exact=True,
        )

        balance_visible = balance.is_visible()

        if balance_visible:
            available_actions.append(
                "read_savings_balance"
            )

        return SurfaceObservation(
            screen=screen,
            member_id_entered=member_id_entered,
            search_outcome=search_outcome,
            available_actions=available_actions,
            balance_visible=balance_visible,
        )

    @contextmanager
    def _checked_operation(self):
        if self._request_blocked:
            raise PolicyViolation("Session stopped after a blocked request")

        validate_url(self.page.url)

        try:
            yield
        finally:
            if self._request_blocked:
                raise PolicyViolation(
                    "Browser request blocked by URL policy"
                ) from None

            validate_url(self.page.url)

    def navigate(self, url: str) -> None:
        validate_url(url)

        if self._request_blocked:
            raise PolicyViolation("Session stopped after a blocked request")

        # A new page starts at about:blank, so validate the destination
        # rather than the current page before this initial navigation.
        try:
            self.page.goto(url)
        finally:
            if self._request_blocked:
                raise PolicyViolation(
                    "Navigation blocked by URL policy"
                ) from None

        validate_url(self.page.url)

    def fill(self, label: str, value: str) -> None:
        if label != "Member ID":
            raise PolicyViolation("Fill target is not allowed")

        with self._checked_operation():
            self.page.get_by_label(
                label,
                exact=True,
            ).fill(value)

    def click(self, role: str, name: str) -> None:
        if (role, name) not in ALLOWED_CLICKS:
            raise PolicyViolation("Click target is not allowed")

        with self._checked_operation():
            self.page.get_by_role(
                role,
                name=name,
                exact=True,
            ).click()

    def verify_heading(self, name: str) -> None:
        allowed_headings = {
            "Member details",
            "Savings details",

        }
        if name not in allowed_headings:
            raise PolicyViolation("Checkpoint is not allowed")

        with self._checked_operation():
            heading = self.page.get_by_role(
                "heading",
                name=name,
                exact=True,
            )
            expect(heading).to_be_visible()

        try:
            expect(heading).to_be_visible(
                timeout=5000
            )
        except AssertionError:
            raise PlaywrightTimeoutError(
                f"Heading did not appear:{name}"
            )from None


    def read(self, label: str) -> str:
        if label != "Savings balance":
            raise PolicyViolation("Read target is not allowed")

        with self._checked_operation():
            element = self.page.get_by_label(
                label,
                exact=True,
            )
            return element.inner_text().strip()

    def wait_for_search_outcome(
        self,
    ) -> Literal["found", "not_found"]:
        with self._checked_operation():

            open_member = self.page.get_by_role(
                "link",
                name="Open member",
                exact=True,
            )
            not_found = self.page.get_by_role("status").filter(
                has_text=re.compile(r"^Member not found\.$")
            )

            try:
                expect(open_member.or_(not_found)).to_be_visible(
                    timeout=5000
                )

            except AssertionError:
                raise PlaywrightTimeoutError(
                    "Search outcome did not appear within five seconds"
                ) from None


            if not_found.is_visible():
                return "not_found"

            return "found"

    def safe_snapshot(self) -> dict:
        validate_url(self.page.url)

        known_headings = [
            "Credit Unoin Admin",
            "Search results",
            "Member details",
            "Savings details",
        ]

        known_controls = [
            ("button", "search"),
            ("link", "Open member"),
            ("link", "View savings"),
        ]

        headings = [
            name
            for name in known_headings
            if self.page.get_by_role(
                "heading",
                name=name,
                exact=True,
            ).is_visible()
        ]

        controls = [
            name
            for role, name in known_controls
            if self.page.get_by_role(
                role,
                name=name,
                exact=True,
            ).is_visible()
        ]

        return {
            "title": "Credit Union Admin",
            "headings": headings,
            "controls": controls,
        }
