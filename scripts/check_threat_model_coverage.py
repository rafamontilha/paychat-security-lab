"""Verifica que report/threat_model.md cobre as 21 células da matriz 3×7.

Espera, na seção de rastreabilidade, finding IDs no formato `{variante}_{categoria}`
para cada combinação de 3 variantes (a, b, c) × 7 categorias da matriz baseline.

Exit code 0 quando 21/21 estão presentes; exit code 1 com lista das ausentes.
"""

from __future__ import annotations

import sys
from pathlib import Path

VARIANTS = ("a", "b", "c")
CATEGORIES = (
    "pi_direct",
    "pi_indirect",
    "ioh",
    "model_theft",
    "sensitive_disclosure",
    "insecure_plugin",
    "excessive_agency",
)

THREAT_MODEL_PATH = Path(__file__).resolve().parent.parent / "report" / "threat_model.md"


def expected_cells() -> list[str]:
    return [f"{v}_{c}" for v in VARIANTS for c in CATEGORIES]


def check(threat_model_text: str) -> tuple[list[str], list[str]]:
    expected = expected_cells()
    present = [cell for cell in expected if f"`{cell}`" in threat_model_text]
    missing = [cell for cell in expected if cell not in present]
    return present, missing


def main() -> int:
    if not THREAT_MODEL_PATH.exists():
        print(f"ERRO: {THREAT_MODEL_PATH} não existe", file=sys.stderr)
        return 1

    text = THREAT_MODEL_PATH.read_text(encoding="utf-8")
    present, missing = check(text)

    total = len(VARIANTS) * len(CATEGORIES)
    print(f"{len(present)}/{total} células cobertas em {THREAT_MODEL_PATH.name}")

    if missing:
        print(f"\nFALHA — {len(missing)} célula(s) ausente(s) na tabela de rastreabilidade:")
        for cell in missing:
            print(f"  - {cell}")
        return 1

    print("OK — todas as células da matriz 3×7 estão rastreadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
