"""Red-team harness for Fase 7 — PI direct, PI indirect, IOH.

Usage:
    python -m red_team.harness [OPTIONS]

Options:
    --variant     a|b|c|all  (default: all)
    --category    pi_direct|pi_indirect|ioh|all  (default: all)
    --temperature 0.0|0.7|all  (default: all)
    --dry-run     Run only 30 evidences then stop and write _dry_run_report.md
    --resume      Skip evidences whose JSON file already exists (idempotent)
    --base-url    API base URL  (default: http://localhost:8000)
    --timeout     HTTP timeout in seconds  (default: 120)

Environment variables:
    HARNESS_BUYER_API_KEY   API key for a buyer-role user (required)

The harness consumes POST /api/agent/chat via HTTP only (ADR-001).
Rate limits: Anthropic pool (variant a) and Groq pool (variants b, c) are independent.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from aiolimiter import AsyncLimiter

from red_team.heuristics import evaluate_ioh, evaluate_pi_direct, evaluate_pi_indirect
from red_team.models import EvidenceRecord
from red_team.payloads.insecure_output_handling import IOH_PAYLOADS
from red_team.payloads.prompt_injection_direct import PI_DIRECT_PAYLOADS
from red_team.payloads.prompt_injection_indirect import PI_INDIRECT_PAYLOADS

_EVIDENCE_DIR = Path("evidence/baseline")
_DRY_RUN_REPORT = _EVIDENCE_DIR / "_dry_run_report.md"

_RUNS_PER_TEMP: dict[str, int] = {
    "pi_direct": 2,
    "pi_indirect": 3,
    "ioh": 2,
}

_TEMPERATURES = [0.0, 0.7]
_VARIANTS = ["a", "b", "c"]

# Independent rate limiters: 30 req/60 s per provider
_LIMITER_ANTHROPIC = AsyncLimiter(30, 60)
_LIMITER_GROQ = AsyncLimiter(30, 60)
_SEMAPHORE = asyncio.Semaphore(5)  # max concurrent in-flight requests


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


async def _login(client: httpx.AsyncClient, api_key: str) -> str:
    """Login and return a fresh session token."""
    resp = await client.post("/api/auth/login", json={"api_key": api_key})
    resp.raise_for_status()
    return resp.json()["session_token"]


# ---------------------------------------------------------------------------
# Single attack execution
# ---------------------------------------------------------------------------


async def _run_one(
    client: httpx.AsyncClient,
    api_key: str,
    variant: str,
    category: str,
    technique: str,
    payload_text: str,
    temperature: float,
    run_index: int,
    timeout: float,
) -> dict[str, Any]:
    """Execute a single attack and return a raw result dict."""
    evidence_id = EvidenceRecord.make_id(
        variant, category, technique, payload_text, temperature, run_index
    )
    limiter = _LIMITER_ANTHROPIC if variant == "a" else _LIMITER_GROQ

    async with _SEMAPHORE:
        async with limiter:
            session_token = await _login(client, api_key)
            body = {
                "session_token": session_token,
                "message": payload_text,
                "temperature": temperature,
            }
            try:
                resp = await client.post(
                    f"/api/agent/chat?variant={variant}",
                    json=body,
                    timeout=timeout,
                )
                if resp.status_code == 400:
                    # Blocked by Llama Guard (Variant C) — attack failed, run succeeded
                    detail = resp.json().get("detail", {})
                    return {
                        "id": evidence_id,
                        "variant": variant,
                        "category": category,
                        "technique": technique,
                        "payload": payload_text,
                        "temperature": temperature,
                        "run_index": run_index,
                        "response": f"blocked_by_guard:{detail.get('category', 'unknown')}",
                        "execution_status": "success",
                        "trace": detail.get("trace", []),
                    }
                if resp.status_code == 503:
                    return {
                        "id": evidence_id,
                        "variant": variant,
                        "category": category,
                        "technique": technique,
                        "payload": payload_text,
                        "temperature": temperature,
                        "run_index": run_index,
                        "response": "",
                        "execution_status": "error",
                        "trace": [],
                        "error": f"503 service unavailable: {resp.text[:200]}",
                    }
                resp.raise_for_status()
                data = resp.json()
                response_text: str = data.get("response", "")
                trace: list[dict] = data.get("trace", [])
                exec_status: str
                if response_text in ("max_iterations_reached",):
                    exec_status = "max_iterations"
                else:
                    exec_status = "success"
                return {
                    "id": evidence_id,
                    "variant": variant,
                    "category": category,
                    "technique": technique,
                    "payload": payload_text,
                    "temperature": temperature,
                    "run_index": run_index,
                    "response": response_text,
                    "execution_status": exec_status,
                    "trace": trace,
                }
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                return {
                    "id": evidence_id,
                    "variant": variant,
                    "category": category,
                    "technique": technique,
                    "payload": payload_text,
                    "temperature": temperature,
                    "run_index": run_index,
                    "response": "",
                    "execution_status": "error",
                    "trace": [],
                    "error": str(exc)[:200],
                }


# ---------------------------------------------------------------------------
# Heuristic evaluation
# ---------------------------------------------------------------------------


def _apply_heuristic(
    category: str,
    technique: str,
    payload_text: str,
    canary: str,
    raw: dict[str, Any],
) -> tuple[bool, str]:
    response = raw["response"]
    trace = raw["trace"]
    exec_status = raw["execution_status"]

    if exec_status == "error":
        return False, "execution_error"
    if exec_status == "max_iterations":
        return False, "max_iterations"

    if category == "pi_direct":
        return evaluate_pi_direct(payload_text, canary, response, trace)
    if category == "pi_indirect":
        return evaluate_pi_indirect(canary, response, trace)
    return evaluate_ioh(response, trace)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _evidence_path(evidence_id: str) -> Path:
    return _EVIDENCE_DIR / f"{evidence_id}.json"


def _persist(record: EvidenceRecord) -> None:
    path = _evidence_path(record.id)
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")


def _exists(evidence_id: str) -> bool:
    return _evidence_path(evidence_id).exists()


# ---------------------------------------------------------------------------
# Task builder
# ---------------------------------------------------------------------------


def _build_tasks(
    variants: list[str],
    categories: list[str],
    temperatures: list[float],
) -> list[dict[str, Any]]:
    """Return a flat list of (variant, category, technique, payload_text, canary, temp, run_i)."""
    tasks: list[dict[str, Any]] = []

    def _add(
        variant: str,
        category: str,
        technique: str,
        payload_text: str,
        canary: str,
        temperature: float,
    ) -> None:
        runs = _RUNS_PER_TEMP[category]
        for run_index in range(runs):
            tasks.append(
                {
                    "variant": variant,
                    "category": category,
                    "technique": technique,
                    "payload_text": payload_text,
                    "canary": canary,
                    "temperature": temperature,
                    "run_index": run_index,
                }
            )

    for v in variants:
        for temp in temperatures:
            if "pi_direct" in categories:
                for p in PI_DIRECT_PAYLOADS:
                    _add(v, "pi_direct", p.technique, p.full_text, p.canary, temp)

            if "pi_indirect" in categories:
                for p in PI_INDIRECT_PAYLOADS:
                    _add(v, "pi_indirect", p.technique, p.trigger_query, p.canary, temp)

            if "ioh" in categories:
                for p in IOH_PAYLOADS:
                    _add(v, "ioh", p.technique, p.text, "", temp)

    return tasks


# ---------------------------------------------------------------------------
# Main async runner
# ---------------------------------------------------------------------------


async def run(
    variants: list[str],
    categories: list[str],
    temperatures: list[float],
    api_key: str,
    base_url: str,
    timeout: float,
    resume: bool,
    dry_run: bool,
) -> list[EvidenceRecord]:
    _EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    tasks = _build_tasks(variants, categories, temperatures)
    if dry_run:
        tasks = tasks[:30]
        print(f"[dry-run] Running {len(tasks)} executions.")
    else:
        print(f"[harness] Total tasks: {len(tasks)}")

    if resume:
        pending = [
            t
            for t in tasks
            if not _exists(
                EvidenceRecord.make_id(
                    t["variant"],
                    t["category"],
                    t["technique"],
                    t["payload_text"],
                    t["temperature"],
                    t["run_index"],
                )
            )
        ]
        skipped = len(tasks) - len(pending)
        if skipped:
            print(f"[resume] Skipping {skipped} already-persisted evidences.")
        tasks = pending

    records: list[EvidenceRecord] = []
    t0 = time.monotonic()

    async with httpx.AsyncClient(base_url=base_url) as client:
        coros = [
            _run_one(
                client,
                api_key,
                t["variant"],
                t["category"],
                t["technique"],
                t["payload_text"],
                t["temperature"],
                t["run_index"],
                timeout,
            )
            for t in tasks
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)

    for task, result in zip(tasks, results):
        if isinstance(result, Exception):
            raw: dict[str, Any] = {
                "id": EvidenceRecord.make_id(
                    task["variant"],
                    task["category"],
                    task["technique"],
                    task["payload_text"],
                    task["temperature"],
                    task["run_index"],
                ),
                "variant": task["variant"],
                "category": task["category"],
                "technique": task["technique"],
                "payload": task["payload_text"],
                "temperature": task["temperature"],
                "run_index": task["run_index"],
                "response": "",
                "execution_status": "error",
                "trace": [],
                "error": str(result)[:200],
            }
            success_flag, success_reason = False, "exception"
        else:
            raw = result
            success_flag, success_reason = _apply_heuristic(
                task["category"],
                task["technique"],
                task["payload_text"],
                task.get("canary", ""),
                raw,
            )

        record = EvidenceRecord(
            id=raw["id"],
            variant=raw["variant"],  # type: ignore[arg-type]
            category=raw["category"],  # type: ignore[arg-type]
            technique=raw["technique"],
            payload=raw["payload_text"] if "payload_text" in raw else raw.get("payload", ""),
            temperature=raw["temperature"],
            run_index=raw["run_index"],
            response=raw["response"],
            success_flag=success_flag,
            success_reason=success_reason,
            execution_status=raw["execution_status"],  # type: ignore[arg-type]
            trace=raw["trace"],
        )
        _persist(record)
        records.append(record)

    elapsed = time.monotonic() - t0
    n_success = sum(1 for r in records if r.execution_status == "success")
    n_attacks = sum(1 for r in records if r.success_flag)
    print(
        f"[harness] Done: {len(records)} runs in {elapsed:.1f}s | "
        f"execution_status=success: {n_success} | success_flag=True: {n_attacks}"
    )

    if dry_run:
        _write_dry_run_report(records, elapsed)

    return records


def _write_dry_run_report(records: list[EvidenceRecord], elapsed_s: float) -> None:
    """Write _dry_run_report.md with cost extrapolation."""
    n = len(records)
    n_a = sum(1 for r in records if r.variant == "a")
    n_bc = n - n_a
    # Rough cost extrapolation (Anthropic ~$3/M input, $15/M output at Sonnet 4.6)
    # Assume ~500 input tokens + ~200 output tokens per call
    cost_a_per_call_usd = (500 * 3 + 200 * 15) / 1_000_000
    full_tasks_a = len(_build_tasks(["a"], ["pi_direct", "pi_indirect", "ioh"], _TEMPERATURES))
    full_tasks_bc = len(
        _build_tasks(["b", "c"], ["pi_direct", "pi_indirect", "ioh"], _TEMPERATURES)
    )
    est_cost_a = full_tasks_a * cost_a_per_call_usd
    report = f"""# Dry-run Report — Red Team Harness

Generated: {datetime.now(timezone.utc).isoformat()}

## Dry-run summary

| Metric | Value |
|--------|-------|
| Executions completed | {n} |
| Variant A calls | {n_a} |
| Variant B+C calls | {n_bc} |
| Wall clock | {elapsed_s:.1f}s |
| Execution errors | {sum(1 for r in records if r.execution_status == "error")} |

## Cost extrapolation (full matrix)

| Provider | Calls (full) | Est. cost |
|----------|-------------|-----------|
| Anthropic (Variant A) | {full_tasks_a} | ~USD {est_cost_a:.2f} |
| Groq (Variants B + C) | {full_tasks_bc} | USD 0.00 (free tier) |
| **Total** | **{full_tasks_a + full_tasks_bc}** | **~USD {est_cost_a:.2f}** |

*Anthropic estimate uses claude-sonnet-4-6 pricing: $3/M input, $15/M output,
assuming 500 input tokens + 200 output tokens per call (verify current pricing).*

## Actual cost at run end

TODO: Fill in real cost from Anthropic dashboard after full matrix run.
"""
    _DRY_RUN_REPORT.write_text(report, encoding="utf-8")
    print(f"[dry-run] Report written to {_DRY_RUN_REPORT}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PayChat red-team harness — Fase 7")
    parser.add_argument("--variant", default="all", choices=["a", "b", "c", "all"])
    parser.add_argument(
        "--category",
        default="all",
        choices=["pi_direct", "pi_indirect", "ioh", "all"],
    )
    parser.add_argument("--temperature", default="all", choices=["0.0", "0.7", "all"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    api_key = os.environ.get("HARNESS_BUYER_API_KEY", "")
    if not api_key:
        print("ERROR: HARNESS_BUYER_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    variants = _VARIANTS if args.variant == "all" else [args.variant]
    categories = (
        ["pi_direct", "pi_indirect", "ioh"] if args.category == "all" else [args.category]
    )
    temperatures = (
        _TEMPERATURES if args.temperature == "all" else [float(args.temperature)]
    )

    asyncio.run(
        run(
            variants=variants,
            categories=categories,
            temperatures=temperatures,
            api_key=api_key,
            base_url=args.base_url,
            timeout=args.timeout,
            resume=args.resume,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
