from automation.discovery_models import (
    SurfaceObservation,
)
from automation.llm import OllamaDecisionClient


def main():
    client = OllamaDecisionClient()

    observation = SurfaceObservation(
        screen="search",
        member_id_entered=False,
        search_outcome="none",
        available_actions=[
            "fill_member_id",
            "click_search",
        ],
        balance_visible=False,
    )

    decision, decision_id = client.decide(
        goal=(
            "Read the savings balance for "
            "the supplied member ID"
        ),
        observation=observation,
        previous_actions=[],
        output_captured=False,
    )

    print(
        {
            "provider": client.provider,
            "model": client.model,
            "decision_id": decision_id,
            "decision": decision.model_dump(),
        }
    )


if __name__ == "__main__":
    main()