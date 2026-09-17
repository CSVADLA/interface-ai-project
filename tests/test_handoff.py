from automation.handoff import HandoffController


class FakePage:
    def __init__(self):
        self.waited_for = None

    def wait_for_timeout(self, milliseconds):
        self.waited_for = milliseconds


class FakeSurface:
    def __init__(self):
        self.snapshots = [
            {
                "title": "Credit Union Admin",
                "headings": [],
                "controls": ["Open member"],
            },
            {
                "title": "Credit Union Admin",
                "headings": ["Member details"],
                "controls": ["View savings"],
            },
        ]

    def safe_snapshot(self):
        return self.snapshots.pop(0)


class FakeEvidence:
    def __init__(self):
        self.events = []

    def event(self, event, **details):
        self.events.append(
            {
                "event": event,
                **details,
            }
        )


def test_handoff_preserves_session_and_returns_control(monkeypatch):
    page = FakePage()
    surface = FakeSurface()
    evidence = FakeEvidence()

    monkeypatch.setattr("builtins.input", lambda _: "")

    handoff = HandoffController(
        page=page,
        surface=surface,
        evidence=evidence,
    )

    handoff.request(
        reason="Operator review required",
        step_index=3,
        operator_instruction="Click Open member.",
    )

    assert handoff.owner == "automation"
    assert page.waited_for == 250

    assert [
        item["event"]
        for item in evidence.events
    ] == [
        "handoff_requested",
        "human_action_summary",
        "handoff_resumed",
    ]

    session_ids = {
        item["session_id"]
        for item in evidence.events
    }

    assert session_ids == {handoff.session_id}

    assert evidence.events[0]["owner"] == "human"
    assert evidence.events[1]["owner"] == "human"
    assert evidence.events[2]["owner"] == "automation"

    assert evidence.events[1]["before"]["controls"] == [
        "Open member"
    ]
    assert evidence.events[1]["after"]["headings"] == [
        "Member details"
    ]


def test_handoff_rejects_request_when_human_already_has_control():
    page = FakePage()
    surface = FakeSurface()
    evidence = FakeEvidence()

    handoff = HandoffController(
        page=page,
        surface=surface,
        evidence=evidence,
    )
    handoff.owner = "human"

    try:
        handoff.request(
            reason="Duplicate request",
            step_index=3,
            operator_instruction="Click Open member.",
        )
    except RuntimeError as error:
        assert "automation" in str(error).lower()
    else:
        raise AssertionError(
            "Expected a duplicate handoff request to fail"
        )