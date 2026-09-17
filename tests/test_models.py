import pytest
from pydantic import ValidationError

from automation.models import (
    BusinessOutcome,
    SavingsInput,
    SavingsOutput,
    SuccessResult,
    HardFailure,
    RecoverableFailure
)


def test_member_id_preserves_leading_zeros():
    inputs = SavingsInput(member_id="00123")

    assert inputs.member_id == "00123"


@pytest.mark.parametrize(
    "member_id",
    ["abc", "123", "123456", "", " 12345", 12345],
)
def test_invalid_member_ids_are_rejected(member_id):
    with pytest.raises(ValidationError):
        SavingsInput(member_id=member_id)


def test_success_requires_outputs():
    with pytest.raises(ValidationError):
        SuccessResult()


def test_success_serializes_to_expected_contract():
    result = SuccessResult(
        outputs=SavingsOutput(savings_balance="1250.50")
    )

    assert result.model_dump() == {
        "status": "success",
        "code": "completed",
        "outputs": {
            "savings_balance": "1250.50",
            "currency": "USD",
        },
    }


@pytest.mark.parametrize("balance", ["abc", "1.234", "NaN"])
def test_malformed_balances_are_rejected(balance):
    with pytest.raises(ValidationError):
        SavingsOutput(savings_balance=balance)


def test_unknown_business_code_is_rejected():
    with pytest.raises(ValidationError):
        BusinessOutcome(code="unexpected_code")


def test_extra_input_fields_are_rejected():
    with pytest.raises(ValidationError):
        SavingsInput(member_id="12345", password="test-only")

def test_recoverable_failure_contract():
    result = RecoverableFailure(
        step_index=2,
        expected="Search result",
        observed="Timed out waiting for UI",
    )

    assert result.model_dump() == {
        "status": "failure",
        "category": "recoverable",
        "code": "ui_timeout",
        "step_index": 2,
        "expected": "Search result",
        "observed": "Timed out waiting for UI",
    }


def test_hard_failure_contract():
    result = HardFailure(
        code="policy_violation",
        step_index=1,
        expected="Allowed action",
        observed="Blocked by policy",
    )

    assert result.category == "hard"


def test_unknown_failure_code_is_rejected():
    with pytest.raises(ValidationError):
        HardFailure(
            code="random_error",
            expected="Valid execution",
            observed="Unknown state",
        )