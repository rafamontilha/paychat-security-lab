"""Minimal Presidio Analyzer mock for local development.

Implements POST /analyze compatible with the real Presidio HTTP API,
using regex patterns for Brazilian PII entities. Runs on port 3000.

Usage:
    uv run python scripts/presidio_mock.py
"""

from __future__ import annotations

import re
from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Presidio Mock")

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("BR_CPF", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")),
    ("BR_CNPJ", re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")),
    ("PHONE_NUMBER", re.compile(r"\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)(?:9\s?)?\d{4}[-\s]?\d{4}\b")),
    ("EMAIL_ADDRESS", re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")),
]


class AnalyzeRequest(BaseModel):
    text: str
    language: str = "pt"
    entities: list[str] | None = None


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    entities = set(req.entities) if req.entities else {p[0] for p in _PATTERNS}
    for entity_type, pattern in _PATTERNS:
        if entity_type not in entities:
            continue
        for match in pattern.finditer(req.text):
            results.append(
                {
                    "entity_type": entity_type,
                    "start": match.start(),
                    "end": match.end(),
                    "score": 0.85,
                    "recognition_metadata": {"recognizer_name": "MockRecognizer"},
                }
            )
    return results


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="warning")
