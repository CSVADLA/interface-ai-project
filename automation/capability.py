from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LabelTarget(StrictModel):
    strategy: Literal["label"] = "label"
    name: str = Field(min_length=1)


class RoleTarget(StrictModel):
    strategy: Literal["role"] = "role"
    role: Literal["button", "link", "heading", "status"]
    name: str = Field(min_length=1)


class FillStep(StrictModel):
    action: Literal["fill"] = "fill"
    target: LabelTarget
    input_parameter: Literal["member_id"] = "member_id"


class ClickStep(StrictModel):
    action: Literal["click"] = "click"
    target: RoleTarget


class SearchOutcomeStep(StrictModel):
    action: Literal["check_search_outcome"] = "check_search_outcome"


Step = Annotated[
    FillStep | ClickStep | SearchOutcomeStep,
    Field(discriminator="action"),
]


class BalanceExtraction(StrictModel):
    field: Literal["savings_balance"] = "savings_balance"
    target: LabelTarget
    format: Literal["decimal_string"] = "decimal_string"


class SavingsCapability(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    name: Literal["read_member_savings"] = "read_member_savings"

    input_contract: Literal["SavingsInput"] = "SavingsInput"
    output_contract: Literal["SavingsOutput"] = "SavingsOutput"

    entry_path: Literal["/"] = "/"
    steps: list[Step] = Field(min_length=1, max_length=20)

    checkpoint: RoleTarget
    extraction: BalanceExtraction
    currency: Literal["USD"] = "USD"