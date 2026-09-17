import pytest
from pathlib import Path
from automation.capability import (
    BalanceExtraction,
    ClickStep,
    FillStep,
    LabelTarget,
    RoleTarget,
    SavingsCapability,
)

from automation.policy import (
    PolicyViolation,
    validate_capability,
    validate_url,
    validate_flow,
    ArtifactFlowError
)


def make_capability(step):
    return SavingsCapability(
        steps=[step],
        checkpoint=RoleTarget(
            role="heading",
            name="Savings details",
        ),
        extraction=BalanceExtraction(
            target=LabelTarget(name="Savings balance"),
        ),
    )


def test_search_click_is_allowed():
    capability = make_capability(
        ClickStep(
            target=RoleTarget(role="button", name="Search")
        )
    )

    validate_capability(capability)


def test_transfer_click_is_blocked():
    capability = make_capability(
        ClickStep(
            target=RoleTarget(role="button", name="Transfer funds")
        )
    )

    with pytest.raises(PolicyViolation):
        validate_capability(capability)


def test_password_fill_is_blocked():
    capability = make_capability(
        FillStep(target=LabelTarget(name="Password"))
    )

    with pytest.raises(PolicyViolation):
        validate_capability(capability)

@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:5000/",
        "http://127.0.0.1:5000/?member_id=12345",
        "http://127.0.0.1:5000/members/12345",
        "http://127.0.0.1:5000/members/12345/savings",
    ],
)
def test_allowed_urls(url):
    validate_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/",
        "http://127.0.0.1:5001/",
        "http://127.0.0.1:5000.evil.example/",
        "http://127.0.0.1:5000/admin",
        "http://127.0.0.1:5000/?member_id=abc",
        "http://127.0.0.1:5000/?member_id=12345&member_id=67890",
        "http://127.0.0.1:5000/?member_id=12345&token=example",
        "http://127.0.0.1:5000/members/12345/transfer",
    ],
)
def test_disallowed_urls(url):
    with pytest.raises(PolicyViolation):
        validate_url(url)

def test_incomplete_flow_is_rejected():
    from automation.capability import SavingsCapability

    artifact = SavingsCapability.model_validate_json(
        (
            Path("examples")
            / "savings.timeout.json"
        ).read_text(encoding="utf-8")
    )

    with pytest.raises(ArtifactFlowError):
        validate_flow(artifact)
