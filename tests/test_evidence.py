import json

from automation.evidence import EvidenceLogger, redact


def test_sensitive_fields_are_redacted():
    value = {
        "member_id": "12345",
        "outputs": {
            "savings_balance": "1250.50",
            "currency": "USD",
        },
        "authorization": "Bearer test-token",
    }

    safe_value = redact(value)

    assert safe_value == {
        "member_id": "[REDACTED]",
        "outputs": {
            "savings_balance": "[REDACTED]",
            "currency": "USD",
        },
        "authorization": "[REDACTED]",
    }


def test_sensitive_values_inside_text_are_redacted():
    message = (
        "Member 12345 has balance 1250.50 "
        "using Bearer test-token"
    )

    assert redact(message) == (
        "Member [REDACTED_ID] has balance "
        "[REDACTED_AMOUNT] using Bearer [REDACTED]"
    )


def test_evidence_logger_creates_jsonl_file(tmp_path):
    logger = EvidenceLogger(
        mode="replay",
        base_directory=tmp_path,
    )

    logger.event(
        "step_completed",
        step_index=1,
        member_id="12345",
    )

    lines = logger.log_path.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 2

    started = json.loads(lines[0])
    completed = json.loads(lines[1])

    assert started["event"] == "run_started"
    assert started["mode"] == "replay"
    assert completed["event"] == "step_completed"
    assert completed["member_id"] == "[REDACTED]"