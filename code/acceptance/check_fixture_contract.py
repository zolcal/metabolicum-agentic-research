"""Local acceptance preflight checks that do not require Hermes itself."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check_source_fixture(path: Path) -> None:
    data = json.loads(path.read_text())
    required = {
        "schema_version",
        "source_id",
        "source_url",
        "source_type",
        "platform",
        "title",
        "retrieved_at",
        "source_language",
        "speaker_or_author",
        "transcript_text",
        "transcript_sha256",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise SystemExit(f"{path}: missing required fields: {missing}")
    digest = hashlib.sha256(data["transcript_text"].encode()).hexdigest()
    if digest != data["transcript_sha256"]:
        raise SystemExit(f"{path}: transcript_sha256 mismatch")


def main() -> int:
    fixtures = sorted((ROOT / "fixtures" / "sources").glob("*.json"))
    if not fixtures:
        raise SystemExit("no source fixtures found")
    for fixture in fixtures:
        check_source_fixture(fixture)
    print(f"checked {len(fixtures)} source fixture(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
