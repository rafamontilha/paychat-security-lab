"""Re-score persisted pi_direct / pi_indirect evidence with the current heuristics.

Fase 9 corrected the pi_direct/pi_indirect success heuristics (refusal-first; a model that
refuses while quoting the attack's canary/terms is no longer counted as a success). This
re-applies the canonical heuristic to already-collected evidence WITHOUT re-calling any model,
so baseline and post-defense matrices use the same scoring. Only success_flag / success_reason
are updated; response, trace and metadata are preserved. The canary is recovered from the
stored payload (the RTCNRY… token is embedded in it).

Usage:
    python -m red_team.rescore_pi                 # preview (no writes), evidence/baseline
    python -m red_team.rescore_pi --apply         # write changes
    python -m red_team.rescore_pi --dir evidence/post_defense --apply
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from red_team.heuristics import evaluate_pi_direct, evaluate_pi_indirect
from red_team.models import EvidenceRecord

_CANARY_RE = re.compile(r"RTCNRY[0-9A-F]{6}")
_PI_CATEGORIES = {"pi_direct", "pi_indirect"}


def _canary_from_payload(payload: str) -> str:
    m = _CANARY_RE.search(payload or "")
    return m.group(0) if m else ""


def _rescore_one(record: dict) -> tuple[bool, str]:
    canary = _canary_from_payload(record.get("payload", ""))
    response = record.get("response", "")
    trace = record.get("trace", [])
    if record["category"] == "pi_direct":
        return evaluate_pi_direct(record.get("payload", ""), canary, response, trace)
    return evaluate_pi_indirect(canary, response, trace)


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-score pi_direct/pi_indirect evidence")
    parser.add_argument("--dir", default="evidence/baseline")
    parser.add_argument("--apply", action="store_true", help="write changes (default: preview)")
    args = parser.parse_args()

    evidence_dir = Path(args.dir)
    changed = 0
    total = 0
    for path in sorted(evidence_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("category") not in _PI_CATEGORIES:
            continue
        total += 1
        new_flag, new_reason = _rescore_one(record)
        if (
            bool(record.get("success_flag")) != new_flag
            or record.get("success_reason") != new_reason
        ):
            changed += 1
            old = f"{record.get('success_flag')}/{record.get('success_reason')}"
            print(f"  {path.name}: {old} -> {new_flag}/{new_reason}")
            if args.apply:
                record["success_flag"] = new_flag
                record["success_reason"] = new_reason
                # Re-serialize via EvidenceRecord so the on-disk format matches the harness
                # exactly (preserves timestamp, key order, unicode handling).
                path.write_text(
                    EvidenceRecord(**record).model_dump_json(indent=2), encoding="utf-8"
                )

    mode = "APPLIED" if args.apply else "PREVIEW (use --apply to write)"
    print(f"\n[{mode}] {args.dir}: {changed}/{total} pi_* records changed.")


if __name__ == "__main__":
    main()
