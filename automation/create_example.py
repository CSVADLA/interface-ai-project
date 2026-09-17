from pathlib import Path

from automation.capability import (
    BalanceExtraction,
    ClickStep,
    FillStep,
    LabelTarget,
    RoleTarget,
    SavingsCapability,
    SearchOutcomeStep,
)


def main():
    capability = SavingsCapability(
        steps=[
            FillStep(
                target=LabelTarget(name="Member ID"),
                input_parameter="member_id",
            ),
            ClickStep(
                target=RoleTarget(role="button", name="Search"),
            ),
            SearchOutcomeStep(),
            ClickStep(
                target=RoleTarget(role="link", name="Open member"),
            ),
            ClickStep(
                target=RoleTarget(role="link", name="View savings"),
            ),
        ],
        checkpoint=RoleTarget(
            role="heading",
            name="Savings details",
        ),
        extraction=BalanceExtraction(
            target=LabelTarget(name="Savings balance"),
        ),
    )

    project_root = Path(__file__).resolve().parent.parent
    output_path = project_root / "examples" / "savings.manual.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        capability.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print(f"Saved hand-authored example: {output_path}")


if __name__ == "__main__":
    main()