"""Variant C — multi-model pipeline: Llama Guard 3 → Llama 3.1 8B → Presidio.

Stage 1: LlamaGuardClient classifies input; unsafe → GuardBlockedError (fail-closed).
Stage 2: VariantBLlama executes the ReAct loop (reused by composition, no duplication).
Stage 3: PresidioClient scans output; block-policy entity → blocked response; redact-policy → <REDACTED:TYPE>.

Each stage appends a TraceStep so the full pipeline trace is observable.
"""

from typing import Any

import chromadb
import redis as redis_lib
from sqlalchemy.orm import Session

from app.agents.variant_c.system_prompt import build_system_prompt  # noqa: F401 (side-effect import OK)
from app.domain.entities.agent_trace import TraceStep
from app.infrastructure.agents.variant_b_llama import VariantBLlama
from app.infrastructure.defenses.llama_guard import (
    GuardBlockedError,
    GuardVerdict,
    LlamaGuardClient,
)
from app.infrastructure.defenses.presidio import PresidioClient, RedactionResult


class VariantCPipeline:
    def __init__(
        self,
        actor_context: dict[str, Any],
        db: Session,
        chroma: chromadb.ClientAPI,
        redis_client: redis_lib.Redis,
    ) -> None:
        self._actor_context = actor_context
        self._guard = LlamaGuardClient()
        self._agent = VariantBLlama(
            actor_context=actor_context,
            db=db,
            chroma=chroma,
            redis_client=redis_client,
        )
        self._presidio = PresidioClient()

    def run(self, message: str) -> tuple[str, list[TraceStep]]:
        """Execute the three-stage pipeline.

        Returns (final_response, trace) where trace contains steps from all three stages.
        Raises GuardBlockedError if stage 1 rejects the input (caller converts to HTTP 400).
        Raises GuardUnavailableError or PresidioUnavailableError on infra failure (HTTP 503).
        """
        trace: list[TraceStep] = []

        # --- Stage 1: Llama Guard input classification ---
        verdict: GuardVerdict = self._guard.classify_input(message)
        trace.append(
            TraceStep(
                type="guard_verdict",
                content="safe" if verdict.safe else f"unsafe:{verdict.category}",
                guard_categories=[verdict.category] if verdict.category else [],
            )
        )
        if not verdict.safe:
            raise GuardBlockedError(category=verdict.category, raw_response=verdict.raw_response)

        # --- Stage 2: ReAct loop (Llama 3.1 8B via Groq) ---
        agent_response, agent_trace = self._agent.run(message)
        trace.extend(agent_trace)

        # --- Stage 3: Presidio output filter ---
        redaction: RedactionResult = self._presidio.analyze_and_redact(agent_response)
        trace.append(
            TraceStep(
                type="presidio_findings",
                content="blocked" if redaction.blocked else f"{len(redaction.findings)} finding(s)",
                pii_entities=[
                    {
                        "entity_type": f.entity_type,
                        "start": f.start,
                        "end": f.end,
                        "score": f.score,
                    }
                    for f in redaction.findings
                ],
            )
        )

        return redaction.redacted_text, trace
