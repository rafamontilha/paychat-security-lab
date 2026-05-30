"""Verifica a cobertura do relatório executivo report/SECURITY_AUDIT.md.

Dois checks (ambos merge blockers da Fase 11):

1. **Cobertura 21/21** — cada célula `{variante}_{categoria}` da matriz 3×7 aparece como
   finding ID (entre crases) no relatório, consistente com a rastreabilidade do threat_model.md.
2. **Figuras sem link quebrado** — toda imagem referenciada no relatório
   (sintaxe Markdown `![...](caminho)`) existe no disco, relativa a `report/`.

Exit code 0 quando tudo passa; 1 com a lista do que falta.
"""

from __future__ import annotations

import re
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

REPORT_DIR = Path(__file__).resolve().parent.parent / "report"
AUDIT_PATH = REPORT_DIR / "SECURITY_AUDIT.md"

# Captura o caminho de imagens Markdown: ![alt](caminho "título opcional")
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)")


def expected_cells() -> list[str]:
    return [f"{v}_{c}" for v in VARIANTS for c in CATEGORIES]


def check_cells(text: str) -> list[str]:
    """Retorna a lista de células ausentes (esperadas mas não presentes como `id`)."""
    return [cell for cell in expected_cells() if f"`{cell}`" not in text]


def check_figures(text: str) -> list[str]:
    """Retorna a lista de imagens referenciadas que não existem no disco."""
    missing: list[str] = []
    for raw in _IMAGE_RE.findall(text):
        path = raw.strip()
        if path.startswith(("http://", "https://", "data:")):
            continue
        resolved = (REPORT_DIR / path).resolve()
        if not resolved.exists():
            missing.append(path)
    return missing


def main() -> int:
    if not AUDIT_PATH.exists():
        print(f"ERRO: {AUDIT_PATH} não existe", file=sys.stderr)
        return 1

    text = AUDIT_PATH.read_text(encoding="utf-8")
    missing_cells = check_cells(text)
    missing_figs = check_figures(text)

    total = len(VARIANTS) * len(CATEGORIES)
    covered = total - len(missing_cells)
    print(f"{covered}/{total} células rastreadas em {AUDIT_PATH.name}")

    failed = False
    if missing_cells:
        failed = True
        print(f"\nFALHA — {len(missing_cells)} célula(s) sem finding ID no relatório:")
        for cell in missing_cells:
            print(f"  - {cell}")

    if missing_figs:
        failed = True
        print(f"\nFALHA — {len(missing_figs)} figura(s) referenciada(s) inexistente(s):")
        for fig in missing_figs:
            print(f"  - {fig}")

    if failed:
        return 1

    print("OK — 21/21 células rastreadas e todas as figuras existem.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
