import argparse
from decimal import Decimal
from playwright.sync_api import sync_playwright
from pydantic import ValidationError

from automation.models import (
    BusinessOutcome,
    SavingsInput,
    SavingsOutput,
    SuccessResult,
)
from automation.surface import PlaywrightSurface


def read_savings(member_id):
    try:
        inputs = SavingsInput(member_id=member_id)
    except ValidationError:
        return BusinessOutcome(code="invalid_member_id")

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
            surface = PlaywrightSurface(page)

            surface.navigate("http://127.0.0.1:5000")
            surface.fill("Member ID", inputs.member_id)
            surface.click("button", "Search")

            outcome = surface.wait_for_search_outcome()

            if outcome == "not_found":
                return BusinessOutcome(code="member_not_found")

            surface.click("link", "Open member")
            surface.click("link", "View savings")
            surface.verify_heading("Savings details")

            balance_text = surface.read("Savings balance")
            balance = Decimal(balance_text)

            return SuccessResult(
                outputs=SavingsOutput(
                    savings_balance=str(balance),
                )
            )

        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--member-id", required=True)
    args = parser.parse_args()

    result = read_savings(args.member_id)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()