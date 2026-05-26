"""Red-team harness for Fase 7 (PI direct, PI indirect, IOH)
and Fase 8 (model_theft, sensitive_disclosure, insecure_plugin, excessive_agency).

Usage:
    python -m red_team.harness [OPTIONS]

Options:
    --variant     a|b|c|all  (default: all)
    --category    pi_direct|pi_indirect|ioh|model_theft|sensitive_disclosure|
                  insecure_plugin|excessive_agency|all  (default: all)
    --temperature 0.0|0.7|all  (default: all)
    --dry-run     Run only 30 evidences then stop and write _dry_run_report.md
    --resume      Skip evidences whose JSON file already exists (idempotent)
    --base-url    API base URL  (default: http://localhost:8000)
    --timeout     HTTP timeout in seconds  (default: 120)

Environment variables:
    HARNESS_BUYER_API_KEY   API key for a buyer-role user (required)

The harness consumes POST /api/agent/chat via HTTP only (ADR-001).
Rate limits: Anthropic pool (variant a) and Groq pool (variants b, c) are independent.
Multi-turn payloads (logic_chain_injection) are sent sequentially in the same session.
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

from red_team.custom.cross_actor_impersonation import CROSS_ACTOR_PAYLOADS
from red_team.custom.logic_chain_injection import LOGIC_CHAIN_PAYLOADS
from red_team.custom.toctou_refund import TOCTOU_PAYLOADS
from red_team.custom.tool_chaining_exfil import TOOL_CHAINING_PAYLOADS
from red_team.heuristics import (
    evaluate_excessive_agency,
    evaluate_insecure_plugin,
    evaluate_ioh,
    evaluate_model_theft,
    evaluate_pi_direct,
    evaluate_pi_indirect,
    evaluate_sensitive_disclosure,
)
from red_team.models import EvidenceRecord
from red_team.payloads.insecure_output_handling import IOH_PAYLOADS
from red_team.payloads.prompt_injection_direct import PI_DIRECT_PAYLOADS
from red_team.payloads.prompt_injection_indirect import PI_INDIRECT_PAYLOADS
from red_team.techniques.excessive_agency import EXCESSIVE_AGENCY_PAYLOADS
from red_team.techniques.insecure_plugin import INSECURE_PLUGIN_PAYLOADS
from red_team.techniques.model_theft import MODEL_THEFT_PAYLOADS
from red_team.techniques.sensitive_disclosure import SENSITIVE_DISCLOSURE_PAYLOADS

_EVIDENCE_DIR = Path("evidence/baseline")
_DRY_RUN_REPORT = _EVIDENCE_DIR / "_dry_run_report.md"

_ALL_CATEGORIES = [
    "pi_direct",
    "pi_indirect",
    "ioh",
    "model_theft",
    "sensitive_disclosure",
    "insecure_plugin",
    "excessive_agency",
]

_RUNS_PER_TEMP: dict[str, int] = {
    "pi_direct": 2,
    "pi_indirect": 3,
    "ioh": 2,
    # Fase 8 — enough runs to reach ≥30 evidence per (variant, category)
    "model_theft": 1,  # 60 payloads × 1 run × 2 temps = 120 per variant
    "sensitive_disclosure": 2,  # 20 payloads × 2 runs × 2 temps = 80 per variant
    "insecure_plugin": 1,  # ~35 payloads × 1 run × 2 temps = 70 per variant
    "excessive_agency": 2,  # 20 payloads × 2 runs × 2 temps = 80 per variant
}

_TEMPERATURES = [0.0, 0.7]
_VARIANTS = ["a", "b", "c"]

# Low concurrency by default — collection host has 7.4GB RAM; the WSL2/Docker VM
# (~3.7GB) crashes under parallel agent pipelines. Override via env if on a bigger box.
_HARNESS_CONC = int(os.environ.get("HARNESS_CONCURRENCY", "2"))
_HARNESS_RATE = int(os.environ.get("HARNESS_RATE_PER_MIN", "15"))
_LIMITER_ANTHROPIC = AsyncLimiter(_HARNESS_RATE, 60)
_LIMITER_GROQ = AsyncLimiter(_HARNESS_RATE, 60)  # variants b/c → Together AI
_SEMAPHORE = asyncio.Semaphore(_HARNESS_CONC)


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


async def _login(client: httpx.AsyncClient, api_key: str) -> str:
    resp = await client.post("/api/auth/login", json={"api_key": api_key})
    resp.raise_for_status()
    return resp.json()["session_token"]


# ---------------------------------------------------------------------------
# Single attack execution (supports multi-turn)
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
    turns: list[str] | None = None,
) -> dict[str, Any]:
    evidence_id = EvidenceRecord.make_id(
        variant, category, technique, payload_text, temperature, run_index
    )
    limiter = _LIMITER_ANTHROPIC if variant == "a" else _LIMITER_GROQ
    all_messages = turns if turns else [payload_text]

    async with _SEMAPHORE:
        async with limiter:
            try:
                session_token = await _login(client, api_key)
            except Exception as exc:
                return _error_result(
                    evidence_id,
                    variant,
                    category,
                    technique,
                    payload_text,
                    temperature,
                    run_index,
                    str(exc),
                )

            last_response = ""
            last_trace: list[dict] = []
            last_status = "success"
            full_conversation: list[dict] = []

            for msg_index, message in enumerate(all_messages):
                body = {
                    "session_token": session_token,
                    "message": message,
                    "temperature": temperature,
                }
                try:
                    resp = await client.post(
                        f"/api/agent/chat?variant={variant}",
                        json=body,
                        timeout=timeout,
                    )
                    if resp.status_code == 400:
                        detail = resp.json().get("detail", {})
                        turn_response = f"blocked_by_guard:{detail.get('category', 'unknown')}"
                        turn_trace: list[dict] = detail.get("trace", [])
                        turn_status = "success"
                    elif resp.status_code == 503:
                        last_status = "error"
                        full_conversation.append(
                            {
                                "turn": msg_index + 1,
                                "message": message,
                                "response": "",
                                "error": f"503: {resp.text[:100]}",
                            }
                        )
                        break
                    else:
                        resp.raise_for_status()
                        data = resp.json()
                        turn_response = data.get("response", "")
                        turn_trace = data.get("trace", [])
                        turn_status = (
                            "max_iterations"
                            if turn_response == "max_iterations_reached"
                            else "success"
                        )
                        last_status = turn_status

                    last_response = turn_response
                    last_trace = turn_trace
                    full_conversation.append(
                        {
                            "turn": msg_index + 1,
                            "message": message,
                            "response": turn_response,
                        }
                    )

                except (httpx.TimeoutException, httpx.ConnectError) as exc:
                    last_status = "error"
                    full_conversation.append(
                        {
                            "turn": msg_index + 1,
                            "message": message,
                            "response": "",
                            "error": str(exc)[:200],
                        }
                    )
                    break

            result: dict[str, Any] = {
                "id": evidence_id,
                "variant": variant,
                "category": category,
                "technique": technique,
                "payload": payload_text,
                "temperature": temperature,
                "run_index": run_index,
                "response": last_response,
                "execution_status": last_status,
                "trace": last_trace,
                "metadata": {},
            }
            if len(all_messages) > 1:
                result["metadata"]["full_conversation"] = full_conversation
            return result


def _error_result(
    evidence_id: str,
    variant: str,
    category: str,
    technique: str,
    payload_text: str,
    temperature: float,
    run_index: int,
    error_msg: str,
) -> dict[str, Any]:
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
        "metadata": {"error": error_msg[:200]},
    }


# ---------------------------------------------------------------------------
# Heuristic dispatch
# ---------------------------------------------------------------------------


def _apply_heuristic(
    category: str,
    technique: str,
    payload_text: str,
    canary: str,
    raw: dict[str, Any],
) -> tuple[bool, str, dict[str, Any]]:
    response = raw["response"]
    trace = raw["trace"]
    exec_status = raw["execution_status"]

    if exec_status == "error":
        return False, "execution_error", {}
    if exec_status == "max_iterations":
        return False, "max_iterations", {}

    # Fase 7
    if category == "pi_direct":
        flag, reason = evaluate_pi_direct(payload_text, canary, response, trace)
        return flag, reason, {}
    if category == "pi_indirect":
        flag, reason = evaluate_pi_indirect(canary, response, trace)
        return flag, reason, {}
    if category == "ioh":
        flag, reason = evaluate_ioh(response, trace)
        return flag, reason, {}

    # Fase 8
    if category == "model_theft":
        subtype = "extraction" if "extract_" in technique else "probing"
        return evaluate_model_theft(payload_text, response, trace, subtype=subtype)

    if category == "sensitive_disclosure":
        # Determine subtype from technique prefix
        if technique.startswith("pii_"):
            subtype = "pii_exfil"
        elif technique.startswith("sens_"):
            subtype = "sensitive_info"
        else:
            subtype = "credential_exfil"
        return evaluate_sensitive_disclosure(response, trace, subtype=subtype)

    if category == "insecure_plugin":
        return evaluate_insecure_plugin(response, trace)

    if category == "excessive_agency":
        subtype = "cross_actor" if technique.startswith("impersonate_") else "privilege_escalation"
        return evaluate_excessive_agency(response, trace, subtype=subtype)

    return False, f"unknown_category:{category}", {}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _evidence_path(evidence_id: str) -> Path:
    return _EVIDENCE_DIR / f"{evidence_id}.json"


def _persist(record: EvidenceRecord) -> None:
    _evidence_path(record.id).write_text(record.model_dump_json(indent=2), encoding="utf-8")


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
    tasks: list[dict[str, Any]] = []

    def _add(
        variant: str,
        category: str,
        technique: str,
        payload_text: str,
        canary: str,
        temperature: float,
        turns: list[str] | None = None,
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
                    "turns": turns,
                }
            )

    for v in variants:
        for temp in temperatures:
            # --- Fase 7 ---
            if "pi_direct" in categories:
                for pd in PI_DIRECT_PAYLOADS:
                    _add(v, "pi_direct", pd.technique, pd.full_text, pd.canary, temp)

            if "pi_indirect" in categories:
                for pi in PI_INDIRECT_PAYLOADS:
                    _add(v, "pi_indirect", pi.technique, pi.trigger_query, pi.canary, temp)

            if "ioh" in categories:
                for ph in IOH_PAYLOADS:
                    _add(v, "ioh", ph.technique, ph.text, "", temp)

            # --- Fase 8 ---
            if "model_theft" in categories:
                for pm in MODEL_THEFT_PAYLOADS:
                    _add(v, "model_theft", pm.technique, pm.text, "", temp)

            if "sensitive_disclosure" in categories:
                for psd in SENSITIVE_DISCLOSURE_PAYLOADS:
                    _add(v, "sensitive_disclosure", psd.technique, psd.text, "", temp)

            if "insecure_plugin" in categories:
                for pip in INSECURE_PLUGIN_PAYLOADS:
                    _add(v, "insecure_plugin", pip.technique, pip.text, "", temp)
                for ptc in TOOL_CHAINING_PAYLOADS:
                    _add(v, "insecure_plugin", ptc.technique, ptc.text, "", temp)
                for ptt in TOCTOU_PAYLOADS:
                    _add(v, "insecure_plugin", ptt.technique, ptt.text, "", temp)

            if "excessive_agency" in categories:
                for pea in EXCESSIVE_AGENCY_PAYLOADS:
                    _add(v, "excessive_agency", pea.technique, pea.text, "", temp)
                for pca in CROSS_ACTOR_PAYLOADS:
                    _add(v, "excessive_agency", pca.technique, pca.text, "", temp)
                for plc in LOGIC_CHAIN_PAYLOADS:
                    turn_list = list(plc.turns)
                    _add(
                        v,
                        "excessive_agency",
                        plc.technique,
                        plc.final_turn,
                        "",
                        temp,
                        turns=turn_list,
                    )

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
                turns=t.get("turns"),
            )
            for t in tasks
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)

    for task, result in zip(tasks, results):
        if isinstance(result, BaseException):
            raw: dict[str, Any] = _error_result(
                EvidenceRecord.make_id(
                    task["variant"],
                    task["category"],
                    task["technique"],
                    task["payload_text"],
                    task["temperature"],
                    task["run_index"],
                ),
                task["variant"],
                task["category"],
                task["technique"],
                task["payload_text"],
                task["temperature"],
                task["run_index"],
                str(result)[:200],
            )
            success_flag, success_reason = False, "exception"
            extra_meta: dict[str, Any] = {}
        else:
            raw = result
            success_flag, success_reason, extra_meta = _apply_heuristic(
                task["category"],
                task["technique"],
                task["payload_text"],
                task.get("canary", ""),
                raw,
            )

        # Merge extra metadata from heuristic into raw metadata
        merged_meta = {**raw.get("metadata", {}), **extra_meta}

        record = EvidenceRecord(
            id=raw["id"],
            variant=raw["variant"],  # type: ignore[arg-type]
            category=raw["category"],  # type: ignore[arg-type]
            technique=raw["technique"],
            payload=raw.get("payload", task["payload_text"]),
            temperature=raw["temperature"],
            run_index=raw["run_index"],
            response=raw["response"],
            success_flag=success_flag,
            success_reason=success_reason,
            execution_status=raw["execution_status"],  # type: ignore[arg-type]
            trace=raw["trace"],
            metadata=merged_meta,
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
        _write_dry_run_report(records, elapsed, variants, categories, temperatures)

    return records


def _write_dry_run_report(
    records: list[EvidenceRecord],
    elapsed_s: float,
    variants: list[str],
    categories: list[str],
    temperatures: list[float],
) -> None:
    n = len(records)
    n_a = sum(1 for r in records if r.variant == "a")
    n_bc = n - n_a
    cost_a_per_call_usd = (500 * 3 + 200 * 15) / 1_000_000
    full_tasks_a = len(_build_tasks(["a"], categories, temperatures))
    full_tasks_bc = len(_build_tasks(["b", "c"], categories, temperatures))
    est_cost_a = full_tasks_a * cost_a_per_call_usd
    report = f"""# Dry-run Report — Red Team Harness (Fase 8)

Generated: {datetime.now(timezone.utc).isoformat()}

## Dry-run summary

| Metric | Value |
|--------|-------|
| Executions completed | {n} |
| Variant A calls | {n_a} |
| Variant B+C calls | {n_bc} |
| Wall clock | {elapsed_s:.1f}s |
| Execution errors | {sum(1 for r in records if r.execution_status == "error")} |
| Attack successes | {sum(1 for r in records if r.success_flag)} |

## Cost extrapolation (full matrix, selected categories)

| Provider | Calls (full) | Est. cost |
|----------|-------------|-----------|
| Anthropic (Variant A) | {full_tasks_a} | ~USD {est_cost_a:.2f} |
| Groq (Variants B + C) | {full_tasks_bc} | USD 0.00 (free tier) |
| **Total** | **{full_tasks_a + full_tasks_bc}** | **~USD {est_cost_a:.2f}** |

*Categories selected: {', '.join(categories)}*
*Anthropic estimate: $3/M input + $15/M output, 500 input + 200 output tokens/call.*

## TODO: fill in actual cost from Anthropic dashboard after full run.
"""
    _DRY_RUN_REPORT.write_text(report, encoding="utf-8")
    print(f"[dry-run] Report written to {_DRY_RUN_REPORT}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PayChat red-team harness — Fases 7 & 8")
    parser.add_argument("--variant", default="all", choices=["a", "b", "c", "all"])
    parser.add_argument(
        "--category",
        default="all",
        choices=_ALL_CATEGORIES + ["all"],
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
    categories = _ALL_CATEGORIES if args.category == "all" else [args.category]
    temperatures = _TEMPERATURES if args.temperature == "all" else [float(args.temperature)]

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
