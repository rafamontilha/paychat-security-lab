"""Validate all evidence JSON files against EvidenceRecord schema.

Usage:
    python -m red_team.validate_evidence [--dir evidence/baseline]

Exits with code 1 if any file fails validation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from red_team.models import EvidenceRecord


def validate_dir(evidence_dir: Path) -> tuple[int, int, list[str]]:
    """Return (ok_count, error_count, error_messages)."""
    files = sorted(evidence_dir.glob("*.json"))
    ok, errors, messages = 0, 0, []

    for f in files:
        try:
            data = f.read_text(encoding="utf-8")
            EvidenceRecord.model_validate_json(data)
            ok += 1
        except ValidationError as exc:
            errors += 1
            messages.append(f"{f.name}: {exc.error_count()} validation error(s)\n  {exc}")
        except Exception as exc:
            errors += 1
            messages.append(f"{f.name}: {type(exc).__name__}: {exc}")

    return ok, errors, messages


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate evidence/baseline/*.json")
    parser.add_argument(
        "--dir", default="evidence/baseline", help="Directory containing evidence JSON files"
    )
    args = parser.parse_args()

    evidence_dir = Path(args.dir)
    if not evidence_dir.exists():
        print(f"ERROR: directory not found: {evidence_dir}", file=sys.stderr)
        sys.exit(1)

    ok, errors, messages = validate_dir(evidence_dir)
    total = ok + errors

    print(f"Validated {total} file(s): {ok} OK, {errors} error(s).")

    if messages:
        print()
        for msg in messages:
            print(f"[FAIL] {msg}")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
