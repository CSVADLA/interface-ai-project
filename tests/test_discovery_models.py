import pytest
from pydantic import ValidationError
from automation.discovery_models import DiscoveryDecision, SurfaceObservation


def test_valid_discovery_decision():
    decision = DiscoveryDecision(
        action="click_search",
        reason="search_required",
    )

    assert decision.action == "click_search"


def test_arbitrary_action_is_rejected():
    with pytest.raises(ValidationError):
        DiscoveryDecision(
            action="run_javascript",
            reason="search_required",
        )


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        DiscoveryDecision(
            action="click_search",
            reason="search_required",
            selector="#submit",
        )

def test_observation_contains_no_sensitive_values():
    observation = SurfaceObservation(
        screen="search",
        member_id_entered=True,
        search_outcome="none",
        available_actions=["click_search"],
        balance_visible=False,
    )

    serialized = observation.model_dump_json()

    assert "12345" not in serialized
    assert "1250.50" not in serialized