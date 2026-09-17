import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


SENSITIVE_KEYS = {
    "member_id",
    "savings_balance",
    "password",
    "token",
    "secret",
    "authorization",
}


def redact(value, key=None):
    if key and key.lower() in SENSITIVE_KEYS:
        return "[REDACTED]"

    if isinstance(value, dict):
        return {
            item_key: redact(item_value, item_key)
            for item_key, item_value in value.items()
        }

    if isinstance(value, list):
        return [redact(item) for item in value]

    if isinstance(value, str):
        value = re.sub(
            r"\b[0-9]{5}\b",
            "[REDACTED_ID]",
            value,
        )
        value = re.sub(
            r"\b[0-9]+\.[0-9]{2}\b",
            "[REDACTED_AMOUNT]",
            value,
        )
        value = re.sub(
            r"Bearer\s+\S+",
            "Bearer [REDACTED]",
            value,
            flags=re.IGNORECASE,
        )

    return value


class EvidenceLogger:
    def __init__(
        self,
        mode: str,
        base_directory: Path | None = None,
    ):
        if base_directory is None:
            base_directory = Path("evidence") / "runs"

        timestamp = datetime.now(
            timezone.utc
        ).strftime("%Y%m%dT%H%M%SZ")

        self.run_id = f"{timestamp}-{uuid4().hex[:8]}"
        self.run_directory = base_directory / self.run_id
        self.run_directory.mkdir(
            parents=True,
            exist_ok=False,
        )

        self.log_path = (
            self.run_directory / "events.jsonl"
        )

        self.event(
            "run_started",
            mode=mode,
        )

    def snapshot(
        self,
        name: str,
        snapshot: dict,
    ) -> Path:
        snapshot_path = (
            self.run_directory / f"{name}.json"
        )

        snapshot_path.write_text(
            json.dumps(
                redact(snapshot),
                indent=2,
            ),
            encoding="utf-8",
        )

        self.event(
            "snapshot_saved",
            snapshot=name,
        )

        return snapshot_path

    def event(self, event_name: str, **details) -> None:
        record = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "run_id": self.run_id,
            "event": event_name,
            **details,
        }

        safe_record = redact(record)

        with self.log_path.open(
            "a",
            encoding="utf-8",
        ) as log_file:
            log_file.write(
                json.dumps(safe_record) + "\n"
            )

    def snapshot(
        self,
        name: str,
        snapshot: dict,
    ) -> Path:
        snapshot_path = (
            self.run_directory / f"{name}.json"
        )

        snapshot_path.write_text(
            json.dumps(
                redact(snapshot),
                indent=2,
            ),
            encoding="utf-8",
        )

        self.event(
            "snapshot_saved",
            snapshot=name,
        )

        return snapshot_path