from types import SimpleNamespace

from automation.discovery_models import (
    SurfaceObservation,
)
from automation.llm import OllamaDecisionClient


class FakeOllamaClient:
    def __init__(self):
        self.last_request = None

    def chat(self, **request):
        self.last_request = request

        return SimpleNamespace(
            message=SimpleNamespace(
                content=(
                    '{"action":"click_search",'
                    '"reason":"search_required"}'
                )
            )
        )


def test_ollama_decision_is_validated():
    fake_client = FakeOllamaClient()

    client = OllamaDecisionClient(
        model="test-model",
        client=fake_client,
    )

    observation = SurfaceObservation(
        screen="search",
        member_id_entered=True,
        search_outcome="none",
        available_actions=[
            "click_search",
            "check_search_outcome",
        ],
        balance_visible=False,
    )

    decision, decision_id = client.decide(
        goal=(
            "Read the savings balance for "
            "the supplied member ID"
        ),
        observation=observation,
        previous_actions=["fill_member_id"],
        output_captured=False,
    )

    assert decision.action == "click_search"
    assert decision.reason == "search_required"
    assert decision_id.startswith("ollama-")

    request = fake_client.last_request

    assert request["model"] == "test-model"
    assert request["options"]["temperature"] == 0
    assert request["think"] is False
    assert request["format"]["type"] == "object"