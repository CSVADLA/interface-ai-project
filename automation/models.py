from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class SavingsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    savings_balance: str = Field(pattern=r"^[0-9]+\.[0-9]{2}$")
    currency: Literal["USD"] = "USD"


class SuccessResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["success"] = "success"
    code: Literal["completed"] = "completed"
    outputs: SavingsOutput


class BusinessOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["business_outcome"] = "business_outcome"
    code: Literal["invalid_member_id", "member_not_found"]
    outputs: None = None

class SavingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str = Field(
        strict=True,
        pattern=r"^[0-9]{5}$",
    )

class RecoverableFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["failure"] = "failure"
    category: Literal["recoverable"] = "recoverable"
    code: Literal["ui_timeout"] = "ui_timeout"
    step_index: int | None = Field(default=None, ge=0)
    expected: str
    observed: str


class HardFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["failure"] = "failure"
    category: Literal["hard"] = "hard"
    code: Literal[
        "policy_violation",
        "invalid_output",
        "unexpected_error",
    ]
    step_index: int | None = Field(default=None, ge=0)
    expected: str
    observed: str

class HumanRequired(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["human_required"] = "human_required"
    code: Literal[
        "model_requested",
        "unsafe_decision",
        "max_steps",
    ]
    step_index: int | None = Field(default=None, ge=0)
    reason: str