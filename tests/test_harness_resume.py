"""Idempotency test for the red-team harness --resume flag.

Simulates:
1. Run harness with N tasks → N evidence files persisted.
2. Interrupt (delete last file to simulate partial run).
3. Run with --resume → missing file is re-created, existing ones are not duplicated.

No network calls are made — the HTTP client is mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from red_team.models import EvidenceRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw_result(variant: str, category: str, technique: str, temp: float, run: int) -> dict:
    return {
        "id": EvidenceRecord.make_id(
            variant, category, technique, f"payload_{technique}", temp, run
        ),
        "variant": variant,
        "category": category,
        "technique": technique,
        "payload_text": f"payload_{technique}",
        "payload": f"payload_{technique}",
        "temperature": temp,
        "run_index": run,
        "response": "Não posso ajudar com isso.",
        "execution_status": "success",
        "trace": [],
    }


def _count_files(evidence_dir: Path) -> int:
    return len(list(evidence_dir.glob("*.json")))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_does_not_duplicate(tmp_path: Path) -> None:
    """After a partial run, --resume fills in missing files without duplicating existing ones."""
    from red_team import harness

    # Use 2 PI direct payloads only for speed
    from red_team.payloads.prompt_injection_direct import PI_DIRECT_PAYLOADS

    mini_tasks = [
        {
            "variant": "a",
            "category": "pi_direct",
            "technique": PI_DIRECT_PAYLOADS[0].technique,
            "payload_text": PI_DIRECT_PAYLOADS[0].full_text,
            "canary": PI_DIRECT_PAYLOADS[0].canary,
            "temperature": 0.0,
            "run_index": 0,
        },
        {
            "variant": "a",
            "category": "pi_direct",
            "technique": PI_DIRECT_PAYLOADS[1].technique,
            "payload_text": PI_DIRECT_PAYLOADS[1].full_text,
            "canary": PI_DIRECT_PAYLOADS[1].canary,
            "temperature": 0.0,
            "run_index": 0,
        },
    ]

    evidence_dir = tmp_path / "evidence" / "baseline"
    evidence_dir.mkdir(parents=True)

    def _fake_path(evidence_id: str) -> Path:
        return evidence_dir / f"{evidence_id}.json"

    def _fake_exists(evidence_id: str) -> bool:
        return _fake_path(evidence_id).exists()

    def _fake_persist(record: EvidenceRecord) -> None:
        _fake_path(record.id).write_text(record.model_dump_json(indent=2), encoding="utf-8")

    # Mock HTTP client: _run_one returns a canned success for each task
    async def _fake_run_one(client, api_key, variant, category, technique, payload_text,
                             temperature, run_index, timeout):
        return {
            "id": EvidenceRecord.make_id(
                variant, category, technique, payload_text, temperature, run_index
            ),
            "variant": variant,
            "category": category,
            "technique": technique,
            "payload_text": payload_text,
            "payload": payload_text,
            "temperature": temperature,
            "run_index": run_index,
            "response": "Não posso ajudar.",
            "execution_status": "success",
            "trace": [],
        }

    with (
        patch("red_team.harness._evidence_path", side_effect=_fake_path),
        patch("red_team.harness._exists", side_effect=_fake_exists),
        patch("red_team.harness._persist", side_effect=_fake_persist),
        patch("red_team.harness._build_tasks", return_value=mini_tasks),
        patch("red_team.harness._run_one", side_effect=_fake_run_one),
    ):
        # First run: complete
        await harness.run(
            variants=["a"],
            categories=["pi_direct"],
            temperatures=[0.0],
            api_key="test-key",
            base_url="http://localhost:8000",
            timeout=30.0,
            resume=False,
            dry_run=False,
        )

        after_first = _count_files(evidence_dir)
        assert after_first == 2, f"Expected 2 files after first run, got {after_first}"

        # Simulate partial run: delete the second file
        second_id = EvidenceRecord.make_id(
            mini_tasks[1]["variant"],
            mini_tasks[1]["category"],
            mini_tasks[1]["technique"],
            mini_tasks[1]["payload_text"],
            mini_tasks[1]["temperature"],
            mini_tasks[1]["run_index"],
        )
        (evidence_dir / f"{second_id}.json").unlink()
        assert _count_files(evidence_dir) == 1

        # Second run with --resume: should re-create the missing file, skip the existing one
        await harness.run(
            variants=["a"],
            categories=["pi_direct"],
            temperatures=[0.0],
            api_key="test-key",
            base_url="http://localhost:8000",
            timeout=30.0,
            resume=True,
            dry_run=False,
        )

    after_resume = _count_files(evidence_dir)
    assert after_resume == 2, f"Expected 2 files after resume, got {after_resume}"


@pytest.mark.asyncio
async def test_resume_with_all_present_skips_all(tmp_path: Path) -> None:
    """If all evidence files already exist, --resume runs 0 tasks."""
    from red_team import harness
    from red_team.payloads.prompt_injection_direct import PI_DIRECT_PAYLOADS

    mini_tasks = [
        {
            "variant": "a",
            "category": "pi_direct",
            "technique": PI_DIRECT_PAYLOADS[0].technique,
            "payload_text": PI_DIRECT_PAYLOADS[0].full_text,
            "canary": PI_DIRECT_PAYLOADS[0].canary,
            "temperature": 0.0,
            "run_index": 0,
        }
    ]

    evidence_dir = tmp_path / "evidence" / "baseline"
    evidence_dir.mkdir(parents=True)

    # Pre-write the evidence file
    existing_id = EvidenceRecord.make_id(
        "a", "pi_direct",
        PI_DIRECT_PAYLOADS[0].technique,
        PI_DIRECT_PAYLOADS[0].full_text,
        0.0, 0,
    )
    existing_record = EvidenceRecord(
        id=existing_id,
        variant="a",
        category="pi_direct",
        technique=PI_DIRECT_PAYLOADS[0].technique,
        payload=PI_DIRECT_PAYLOADS[0].full_text,
        temperature=0.0,
        run_index=0,
        response="existing",
        success_flag=False,
        success_reason="refused",
        execution_status="success",
        trace=[],
    )
    (evidence_dir / f"{existing_id}.json").write_text(
        existing_record.model_dump_json(indent=2), encoding="utf-8"
    )

    def _fake_path(evidence_id: str) -> Path:
        return evidence_dir / f"{evidence_id}.json"

    call_count = {"n": 0}

    async def _fake_run_one(*args, **kwargs):
        call_count["n"] += 1
        return {}

    with (
        patch("red_team.harness._evidence_path", side_effect=_fake_path),
        patch("red_team.harness._exists", side_effect=lambda eid: _fake_path(eid).exists()),
        patch("red_team.harness._persist"),
        patch("red_team.harness._build_tasks", return_value=mini_tasks),
        patch("red_team.harness._run_one", side_effect=_fake_run_one),
    ):
        await harness.run(
            variants=["a"],
            categories=["pi_direct"],
            temperatures=[0.0],
            api_key="test-key",
            base_url="http://localhost:8000",
            timeout=30.0,
            resume=True,
            dry_run=False,
        )

    assert call_count["n"] == 0, "resume=True must skip already-present evidence"


def test_evidence_record_id_determinism() -> None:
    """Same inputs always produce the same ID."""
    id1 = EvidenceRecord.make_id("a", "pi_direct", "dan_v1", "payload", 0.0, 0)
    id2 = EvidenceRecord.make_id("a", "pi_direct", "dan_v1", "payload", 0.0, 0)
    assert id1 == id2
    assert len(id1) == 16


def test_evidence_record_id_different_inputs() -> None:
    """Different inputs produce different IDs."""
    id1 = EvidenceRecord.make_id("a", "pi_direct", "dan_v1", "payload", 0.0, 0)
    id2 = EvidenceRecord.make_id("b", "pi_direct", "dan_v1", "payload", 0.0, 0)
    id3 = EvidenceRecord.make_id("a", "pi_direct", "dan_v1", "payload", 0.7, 0)
    assert id1 != id2
    assert id1 != id3
    assert id2 != id3
