import json
import os
from typing import Protocol
from uuid import uuid4

from ollama import Client

from automation.discovery_models import (
    DiscoveryDecision,
    SurfaceObservation,
)


SYSTEM_PROMPT = """
You operate a read-only synthetic credit-union training UI.

Choose exactly one semantic action from allowed_decisions.

Rules:
- Never invent actions, selectors, URLs, or input values.
- The trusted runtime supplies the member ID.
- The action must appear in allowed_decisions.
- If finish appears in allowed_decisions, choose finish.
- Use request_handoff only when no other safe action can progress.
- After click_search, choose check_search_outcome once.
- If search_outcome is found, open the member.
- On member_details, view savings.
- On savings_details, read the balance.
- Do not repeat read_savings_balance after output_captured is true.
- Return only the requested structured decision.
"""


class DecisionClient(Protocol):
    provider: str
    model: str

    def decide(
        self,
        goal: str,
        observation: SurfaceObservation,
        previous_actions: list[str],
        output_captured: bool,
    ) -> tuple[DiscoveryDecision, str]:
        ...


class OllamaDecisionClient:
    provider = "ollama"

    def __init__(
        self,
        model: str | None = None,
        client: Client | None = None,
    ):
        self.model = (
            model
            or os.getenv(
                "OLLAMA_MODEL",
                "qwen3:4b-instruct",
            )
        )

        self.client = client or Client(
            host=os.getenv(
                "OLLAMA_HOST",
                "http://127.0.0.1:11434",
            )
        )

    def decide(
        self,
        goal: str,
        observation: SurfaceObservation,
        previous_actions: list[str],
        output_captured: bool,
    ) -> tuple[DiscoveryDecision, str]:
        allowed_decisions = [
            action
            for action in observation.available_actions
            if action not in previous_actions
        ]

        if output_captured:
            allowed_decisions = [
                action
                for action in allowed_decisions
                if action != "read_savings_balance"
            ]
            allowed_decisions.append("finish")

        allowed_decisions.append("request_handoff")

        schema = DiscoveryDecision.model_json_schema()

        # Narrow the structured-output schema for this exact state.
        schema["properties"]["action"]["enum"] = (
            allowed_decisions
        )

        payload = {
            "goal": goal,
            "observation": observation.model_dump(),
            "previous_actions": previous_actions,
            "output_captured": output_captured,
            "allowed_decisions": allowed_decisions,
            "output_schema": schema,
        }

        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(payload),
                },
            ],
            format=schema,
            options={
                "temperature": 0,
            },
            think=False,
        )

        content = response.message.content

        if not content:
            raise RuntimeError(
                "Ollama returned an empty decision"
            )

        decision = (
            DiscoveryDecision.model_validate_json(
                content
            )
        )

        if decision.action not in allowed_decisions:
            raise RuntimeError(
                "Ollama returned an unavailable action"
            )

        decision_id = (
            f"ollama-{uuid4().hex[:12]}"
        )

        return decision, decision_id