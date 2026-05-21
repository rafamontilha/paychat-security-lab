"""Variant B system prompt must be byte-identical to Variant A.

This guarantees that differences observed in the 3x6 attack matrix are
attributable to the model, not the prompt.
"""

from app.agents.variant_a.system_prompt import build_system_prompt as build_a
from app.agents.variant_b.system_prompt import build_system_prompt as build_b

_ACTOR = {
    "user_id": 42,
    "role": "buyer",
    "session_token": "test-token",
    "name": "Test User",
}


def test_system_prompts_are_byte_identical() -> None:
    assert build_a(_ACTOR) == build_b(_ACTOR), (
        "Variant B system prompt must be byte-identical to Variant A. "
        "Divergence here would confound the 3x6 comparison matrix."
    )


def test_system_prompt_embeds_actor_context() -> None:
    prompt = build_b(_ACTOR)
    assert str(_ACTOR["user_id"]) in prompt
    assert _ACTOR["role"] in prompt
    assert _ACTOR["name"] in prompt
