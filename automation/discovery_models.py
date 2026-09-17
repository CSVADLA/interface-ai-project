from typing import Literal

from pydantic import BaseModel, ConfigDict


class DiscoveryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "fill_member_id",
        "click_search",
        "check_search_outcome",
        "click_open_member",
        "click_view_savings",
        "read_savings_balance",
        "finish",
        "request_handoff",
    ]

    reason: Literal[
        "member_id_required",
        "search_required",
        "search_result_required",
        "member_record_required",
        "savings_page_required",
        "balance_required",
        "goal_complete",
        "blocked",
    ]

class SurfaceObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    screen: Literal[
        "search",
        "search_result",
        "member_details",
        "savings_details",
        "unknown",
    ]

    member_id_entered: bool

    search_outcome: Literal[
        "none",
        "found",
        "not_found",
    ]

    available_actions: list[
        Literal[
            "fill_member_id",
            "click_search",
            "check_search_outcome",
            "click_open_member",
            "click_view_savings",
            "read_savings_balance",
        ]
    ]

    balance_visible: bool