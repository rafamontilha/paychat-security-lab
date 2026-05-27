"""GPT-2 perplexity detector — flags high-perplexity (likely adversarial) inputs.

Adversarial suffixes (GCG-style), random token soup, and obfuscated payloads tend to
have much higher perplexity under a language model than natural user text. This detector
scores an input with GPT-2 small and rejects it above a threshold.

The model is lazy-loaded: torch/transformers are only imported on first real use, so unit
tests can inject a `scorer` callable and run without the heavy ML deps. On the collection
host the GPT-2 weights (~500 MB RAM) coexist with the Docker stack — load once, reuse.
"""

from collections.abc import Callable
from typing import Any

_MODEL_NAME = "gpt2"
# Threshold calibrated empirically against this app's traffic (GPT-2 is English-trained, so
# legitimate *Portuguese* queries already score high): benign PT marketplace queries measured
# up to ~3840 PPL, fluent injections ("ignore previous…", DAN) score LOW (~80-700) and are
# caught by the Rebuff heuristics instead, while GCG-style adversarial suffixes spike to
# ~34000. So perplexity's job here is the high-entropy/gibberish class; 8000 clears benign PT
# with margin while still flagging GCG-style noise.
_DEFAULT_THRESHOLD = 8000.0

# Process-wide cache so GPT-2 is loaded once, not per request. The router builds a fresh
# DefensePipeline (and PerplexityDetector) per request; without this the weights would
# reload on every defended call, adding seconds of latency across the matrix run.
_MODEL_CACHE: dict[str, Any] = {}


def _load_shared_model() -> dict[str, Any]:
    if "model" not in _MODEL_CACHE:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME)
        model.eval()
        _MODEL_CACHE.update(torch=torch, tokenizer=tokenizer, model=model)
    return _MODEL_CACHE


class PerplexityDetector:
    def __init__(
        self,
        threshold: float = _DEFAULT_THRESHOLD,
        scorer: Callable[[str], float] | None = None,
    ) -> None:
        self._threshold = threshold
        self._scorer = scorer
        # Lazy-loaded ML objects (torch / transformers) — typed Any since the deps are
        # optional (whitebox extra) and dynamically imported only when scoring for real.
        self._model: Any = None
        self._tokenizer: Any = None
        self._torch: Any = None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        cache = _load_shared_model()
        self._torch = cache["torch"]
        self._tokenizer = cache["tokenizer"]
        self._model = cache["model"]

    def perplexity(self, text: str) -> float:
        if self._scorer is not None:
            return self._scorer(text)
        self._ensure_model()
        assert self._torch is not None and self._tokenizer is not None and self._model is not None
        enc = self._tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        input_ids = enc["input_ids"]
        if input_ids.shape[1] < 2:
            return 0.0
        with self._torch.no_grad():
            output = self._model(input_ids, labels=input_ids)
        return float(self._torch.exp(output.loss))

    def check_input(self, text: str) -> tuple[bool, str]:
        """Return (allowed, reason). allowed=False blocks the request.

        Degrades gracefully if torch/transformers are not installed in the runtime (e.g. a
        container image without the whitebox extra): the perplexity gate is skipped rather
        than crashing the request, and the other input-layer defenses still apply."""
        if not text.strip():
            return True, "perplexity_skipped:empty"
        try:
            ppl = self.perplexity(text)
        except ImportError:
            return True, "perplexity_unavailable:no_torch"
        if ppl > self._threshold:
            return False, f"high_perplexity:{ppl:.0f}"
        return True, f"perplexity_ok:{ppl:.0f}"
