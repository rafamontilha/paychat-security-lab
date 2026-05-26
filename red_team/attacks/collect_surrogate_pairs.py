"""Collect query/response pairs from each agent variant for surrogate model training.

Sends queries to POST /api/agent/chat for variants a, b, c and persists the results
as JSONL at evidence/surrogate/{variant}/pairs.jsonl.

Target: 500 pairs per variant.  Variant a → Anthropic; variants b/c → Together AI.
Together uses dynamic rate limits; server-side retries handle transient 429s.

Query pool:
  - All payload texts from Fase 7 and Fase 8 payload catalogs (≈ 200 distinct queries)
  - Neutral knowledge queries padded up to target (geography, history, science)
  - Each query is sent at temperature 0.7 to increase response diversity

Usage:
    HARNESS_BUYER_API_KEY=xxx python -m red_team.attacks.collect_surrogate_pairs
    python -m red_team.attacks.collect_surrogate_pairs --variant a --max-pairs 100
    python -m red_team.attacks.collect_surrogate_pairs --resume
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from aiolimiter import AsyncLimiter

# ---------------------------------------------------------------------------
# Query pool
# ---------------------------------------------------------------------------

_NEUTRAL_QUERIES: list[str] = [
    "Qual é a capital do Brasil?",
    "Explique o que é machine learning em termos simples.",
    "Como funciona um motor de combustão interna?",
    "Quais são as principais causas das mudanças climáticas?",
    "O que é a teoria da relatividade de Einstein?",
    "Como se calcula o IMC?",
    "Quais são as regras básicas do xadrez?",
    "Explique o ciclo da água.",
    "O que é fotossíntese?",
    "Como funciona a internet?",
    "Quais são os planetas do sistema solar?",
    "O que é DNA?",
    "Como se forma um arco-íris?",
    "Explique o que é inflação econômica.",
    "O que é blockchain?",
    "Como funciona uma vacina?",
    "Quais são os três estados da matéria?",
    "O que é inteligência artificial?",
    "Como se forma um furacão?",
    "Explique o que é democracia.",
    "O que é o efeito estufa?",
    "Como funciona a memória humana?",
    "Quais são as propriedades da água?",
    "O que é evolução darwiniana?",
    "Como se produz energia solar?",
    "O que é o Big Bang?",
    "Como funciona um motor elétrico?",
    "Quais são as principais religiões do mundo?",
    "O que é a teoria dos jogos?",
    "Como se faz um bolo de chocolate?",
    "Quais são as vitaminas essenciais para o corpo humano?",
    "Como funciona o sistema imunológico?",
    "O que é gravidade quântica?",
    "Como se forma uma estrela?",
    "Quais são os principais biomas do Brasil?",
    "O que é a lei da oferta e demanda?",
    "Como funciona uma bateria de lítio?",
    "Quais são as fases da lua?",
    "O que é neuroplasticidade?",
    "Como se calcula a velocidade média?",
    "O que é criptografia simétrica?",
    "Como funciona o reconhecimento facial?",
    "Quais são os principais movimentos artísticos do século XX?",
    "O que é um algoritmo?",
    "Como funciona o sistema nervoso central?",
    "Quais são os tipos de energia renovável?",
    "O que é a lei de Newton?",
    "Como se forma um delta fluvial?",
    "Quais são as etapas do método científico?",
    "O que é aprendizado por reforço?",
]

_MARKETPLACE_QUERIES: list[str] = [
    "Como faço para rastrear meu pedido?",
    "Qual é a política de devolução?",
    "Quanto tempo leva para o reembolso ser processado?",
    "Como entro em contato com o vendedor?",
    "Posso alterar o endereço de entrega após o pagamento?",
    "O que faço se o produto chegou danificado?",
    "Como avalio um produto comprado?",
    "Qual é o prazo máximo para solicitar reembolso?",
    "Como funciona a garantia do produto?",
    "Posso cancelar um pedido já enviado?",
    "Como verifico se um vendedor é confiável?",
    "Quais formas de pagamento são aceitas?",
    "Como reporto um produto falsificado?",
    "Existe um programa de fidelidade?",
    "Como filtro produtos por avaliação?",
]


def _build_query_pool() -> list[str]:
    """Assemble all available payload texts plus neutral queries."""
    queries: list[str] = []

    # Import payload catalogs (safe — only reading .text attributes)
    try:
        from red_team.payloads.prompt_injection_direct import PI_DIRECT_PAYLOADS

        queries.extend(p.full_text for p in PI_DIRECT_PAYLOADS)
    except Exception:
        pass

    try:
        from red_team.payloads.prompt_injection_indirect import PI_INDIRECT_PAYLOADS

        queries.extend(p.trigger_query for p in PI_INDIRECT_PAYLOADS)
    except Exception:
        pass

    try:
        from red_team.payloads.insecure_output_handling import IOH_PAYLOADS

        queries.extend(p.text for p in IOH_PAYLOADS)
    except Exception:
        pass

    try:
        from red_team.techniques.model_theft import MODEL_THEFT_PAYLOADS

        queries.extend(p.text for p in MODEL_THEFT_PAYLOADS)
    except Exception:
        pass

    try:
        from red_team.techniques.sensitive_disclosure import SENSITIVE_DISCLOSURE_PAYLOADS

        queries.extend(p.text for p in SENSITIVE_DISCLOSURE_PAYLOADS)
    except Exception:
        pass

    try:
        from red_team.techniques.insecure_plugin import INSECURE_PLUGIN_PAYLOADS

        queries.extend(p.text for p in INSECURE_PLUGIN_PAYLOADS)
    except Exception:
        pass

    try:
        from red_team.techniques.excessive_agency import EXCESSIVE_AGENCY_PAYLOADS

        queries.extend(p.text for p in EXCESSIVE_AGENCY_PAYLOADS)
    except Exception:
        pass

    queries.extend(_NEUTRAL_QUERIES)
    queries.extend(_MARKETPLACE_QUERIES)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

# Concurrency kept low: collection runs on a 7.4GB host where the Docker/WSL2 VM
# (~3.7GB) crashes under parallel agent pipelines. Serial (=1) is proven stable.
_COLLECT_CONC = int(os.environ.get("COLLECT_CONCURRENCY", "1"))
_COLLECT_RATE = int(os.environ.get("COLLECT_RATE_PER_MIN", "12"))
_LIMITER_ANTHROPIC = AsyncLimiter(30, 60)  # variant a → Claude (Anthropic)
_LIMITER_TOGETHER = AsyncLimiter(_COLLECT_RATE, 60)  # variants b/c → Together AI
_SEM_ANTHROPIC = asyncio.Semaphore(3)
_SEM_TOGETHER = asyncio.Semaphore(_COLLECT_CONC)


async def _login(client: httpx.AsyncClient, api_key: str) -> str:
    resp = await client.post("/api/auth/login", json={"api_key": api_key})
    resp.raise_for_status()
    return resp.json()["session_token"]


async def _query_variant(
    client: httpx.AsyncClient,
    api_key: str,
    variant: str,
    query: str,
    temperature: float = 0.7,
    timeout: float = 60.0,
) -> dict[str, Any] | None:
    is_together = variant != "a"
    limiter = _LIMITER_TOGETHER if is_together else _LIMITER_ANTHROPIC
    sem = _SEM_TOGETHER if is_together else _SEM_ANTHROPIC
    async with sem:
        async with limiter:
            try:
                session_token = await _login(client, api_key)
                resp = await client.post(
                    f"/api/agent/chat?variant={variant}",
                    json={
                        "session_token": session_token,
                        "message": query,
                        "temperature": temperature,
                    },
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "query": query,
                        "response": data.get("response", ""),
                        "trace": data.get("trace", []),
                    }
                elif resp.status_code == 400:
                    detail = resp.json().get("detail", {})
                    return {
                        "query": query,
                        "response": f"blocked:{detail.get('category','')}",
                        "trace": [],
                    }
            except Exception as exc:
                return {"query": query, "response": f"error:{exc!s:.100}", "trace": []}
    return None


# ---------------------------------------------------------------------------
# Collection runner
# ---------------------------------------------------------------------------


async def collect(
    variant: str,
    api_key: str,
    base_url: str,
    max_pairs: int,
    resume: bool,
    timeout: float,
) -> list[dict[str, Any]]:
    out_dir = Path(f"evidence/surrogate/{variant}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "pairs.jsonl"

    existing: set[str] = set()
    existing_pairs: list[dict[str, Any]] = []
    if resume and out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                existing.add(row["query"])
                existing_pairs.append(row)
            except Exception:
                pass
        print(f"[collect:{variant}] resume: {len(existing)} already collected")

    queries = _build_query_pool()
    # Cycle queries until we reach max_pairs
    target = max_pairs - len(existing_pairs)
    if target <= 0:
        print(f"[collect:{variant}] already at target ({len(existing_pairs)} pairs)")
        return existing_pairs

    # Build workload — cycle through queries
    workload: list[str] = []
    for q in queries:
        if q not in existing:
            workload.append(q)
    # If not enough unique queries, repeat with cycling
    idx = 0
    while len(workload) < target:
        workload.append(queries[idx % len(queries)] + f" [run {idx // len(queries) + 2}]")
        idx += 1
    workload = workload[:target]

    print(f"[collect:{variant}] querying {len(workload)} pairs…")
    t0 = time.monotonic()

    async with httpx.AsyncClient(base_url=base_url) as client:
        coros = [_query_variant(client, api_key, variant, q, timeout=timeout) for q in workload]
        results = await asyncio.gather(*coros, return_exceptions=True)

    collected: list[dict[str, Any]] = list(existing_pairs)
    with out_path.open("a", encoding="utf-8") as fout:
        for q, result in zip(workload, results):
            if isinstance(result, Exception) or result is None:
                continue
            row = {
                "query": result["query"],
                "response": result["response"],
                "variant": variant,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            collected.append(row)

    elapsed = time.monotonic() - t0
    print(f"[collect:{variant}] done — {len(collected)} total pairs  elapsed={elapsed:.1f}s")
    return collected


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect surrogate training pairs from agent variants"
    )
    parser.add_argument("--variant", choices=["a", "b", "c", "all"], default="all")
    parser.add_argument("--max-pairs", type=int, default=500)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--resume", action="store_true", help="Skip already-collected queries")
    args = parser.parse_args()

    api_key = os.environ.get("HARNESS_BUYER_API_KEY", "")
    if not api_key:
        print("ERROR: HARNESS_BUYER_API_KEY not set")
        raise SystemExit(1)

    variants = ["a", "b", "c"] if args.variant == "all" else [args.variant]
    for v in variants:
        asyncio.run(
            collect(
                variant=v,
                api_key=api_key,
                base_url=args.base_url,
                max_pairs=args.max_pairs,
                resume=args.resume,
                timeout=args.timeout,
            )
        )


if __name__ == "__main__":
    main()
