#!/usr/bin/env python3
"""Smoke test: validate connectivity and response from all three LLM APIs."""

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")

PROMPT = "Reply with exactly three words: security lab ready."


def test_claude() -> None:
    if not ANTHROPIC_KEY:
        print("[SKIP] Claude — ANTHROPIC_API_KEY not set")
        return

    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    t0 = time.monotonic()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=64,
        messages=[{"role": "user", "content": PROMPT}],
    )
    elapsed_ms = (time.monotonic() - t0) * 1000
    text = msg.content[0].text if msg.content else ""
    tokens = msg.usage.input_tokens + msg.usage.output_tokens
    print(f"[OK] Claude Sonnet 4.6 — {elapsed_ms:.0f}ms — {tokens} tokens — {text[:80]!r}")


def test_llama() -> None:
    if not GROQ_KEY:
        print("[SKIP] Llama 3.1 8B — GROQ_API_KEY not set")
        return

    from groq import Groq

    client = Groq(api_key=GROQ_KEY)
    t0 = time.monotonic()
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=64,
        messages=[{"role": "user", "content": PROMPT}],
    )
    elapsed_ms = (time.monotonic() - t0) * 1000
    text = resp.choices[0].message.content or ""
    tokens = resp.usage.total_tokens if resp.usage else 0
    print(f"[OK] Llama 3.1 8B (Groq) — {elapsed_ms:.0f}ms — {tokens} tokens — {text[:80]!r}")


def test_llama_guard() -> None:
    if not GROQ_KEY:
        print("[SKIP] Llama Guard 3 — GROQ_API_KEY not set")
        return

    from groq import Groq

    client = Groq(api_key=GROQ_KEY)
    t0 = time.monotonic()
    resp = client.chat.completions.create(
        model="llama-guard-3-8b",
        max_tokens=16,
        messages=[{"role": "user", "content": "Hello, how are you?"}],
    )
    elapsed_ms = (time.monotonic() - t0) * 1000
    text = resp.choices[0].message.content or ""
    tokens = resp.usage.total_tokens if resp.usage else 0
    print(f"[OK] Llama Guard 3 (Groq)  — {elapsed_ms:.0f}ms — {tokens} tokens — {text[:80]!r}")


def main() -> None:
    print("=== PayChat Security Lab — Smoke Test ===\n")
    errors: list[str] = []

    for name, fn in [
        ("Claude", test_claude),
        ("Llama", test_llama),
        ("LlamaGuard", test_llama_guard),
    ]:  # noqa: E501
        try:
            fn()
        except Exception as exc:
            msg = f"[FAIL] {name} — {exc}"
            print(msg)
            errors.append(msg)

    print()
    if errors:
        print(f"Smoke test failed ({len(errors)} error(s)). Check your .env keys.")
        sys.exit(1)
    else:
        print("All models responded successfully.")


if __name__ == "__main__":
    main()
