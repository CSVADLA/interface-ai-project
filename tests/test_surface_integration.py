import pytest
from playwright.sync_api import sync_playwright

from automation.policy import PolicyViolation
from automation.surface import PlaywrightSurface


@pytest.mark.integration
def test_external_link_is_blocked():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        try:
            context = browser.new_context(
                service_workers="block",
            )
            page = context.new_page()
            surface = PlaywrightSurface(page)

            surface.navigate("http://127.0.0.1:5000")
            surface.fill("Member ID", "12345")
            surface.click("button", "Search")

            assert surface.wait_for_search_outcome() == "found"

            # Test setup: simulate an allowed control whose destination
            # has changed to an unapproved external address.
            link = page.get_by_role(
                "link",
                name="Open member",
                exact=True,
            )
            link.evaluate(
                "(element) => "
                "element.href = 'https://example.invalid/'"
            )

            failed_requests = []
            page.on(
                "requestfailed",
                lambda request: failed_requests.append(request.url),
            )

            with pytest.raises(PolicyViolation, match="blocked"):
                surface.click("link", "Open member")

            assert "https://example.invalid/" in failed_requests

            # After a policy violation, the session must stay stopped.
            with pytest.raises(PolicyViolation, match="Session stopped"):
                surface.fill("Member ID", "67890")

        finally:
            browser.close()