import re
from urllib.parse import parse_qs, urlsplit
from automation.capability import (
    ClickStep,
    FillStep,
    SavingsCapability,
    SearchOutcomeStep,
)


class PolicyViolation(Exception):
    """The capability requests an operation we do not allow."""

class ArtifactFlowError(Exception):
    """The recorded steps do not form the supported workflow."""

ALLOWED_CLICKS = {
    ("button", "Search"),
    ("link", "Open member"),
    ("link", "View savings"),
}


def validate_capability(capability: SavingsCapability) -> None:
    for step in capability.steps:
        if isinstance(step, FillStep):
            if step.target.name != "Member ID":
                raise PolicyViolation("Fill target is not allowed")

        elif isinstance(step, ClickStep):
            target = (step.target.role, step.target.name)

            if target not in ALLOWED_CLICKS:
                raise PolicyViolation("Click target is not allowed")

        elif isinstance(step, SearchOutcomeStep):
            pass

        else:
            raise PolicyViolation("Action is not allowed")

    checkpoint = capability.checkpoint

    if (
        checkpoint.role != "heading"
        or checkpoint.name != "Savings details"
    ):
        raise PolicyViolation("Checkpoint is not allowed")

    if capability.extraction.target.name != "Savings balance":
        raise PolicyViolation("Extraction target is not allowed")

def validate_flow(capability: SavingsCapability) -> None:
    expected_flow = [
        ("fill", "Member ID"),
        ("click", "Search"),
        ("check_search_outcome", None),
        ("click", "Open member"),
        ("click", "View savings"),
    ]

    actual_flow = [
        (
            step.action,
            None if isinstance(step, SearchOutcomeStep)
            else step.target.name,
        )
        for step in capability.steps
    ]

    if actual_flow != expected_flow:
        raise ArtifactFlowError(
            "Capability has an incomplete or reordered flow"
        )

def validate_url(url: str) -> None:
    parsed = urlsplit(url)
    path = parsed.path or "/"

    if (
        parsed.scheme != "http"
        or parsed.netloc != "127.0.0.1:5000"
        or parsed.fragment
    ):
        raise PolicyViolation("URL origin is not allowed")

    if path == "/":
        if not parsed.query:
            return

        query = parse_qs(
            parsed.query,
            keep_blank_values=True,
        )

        if set(query) != {"member_id"}:
            raise PolicyViolation("Search parameters are not allowed")

        values = query["member_id"]

        if (
            len(values) != 1
            or re.fullmatch(r"[0-9]{5}", values[0]) is None
        ):
            raise PolicyViolation("Search requires one valid member ID")

        return

    if (
        re.fullmatch(
            r"/members/[0-9]{5}(?:/savings)?",
            path,
        )
        and not parsed.query
    ):
        return

    raise PolicyViolation("URL route is not allowed")
