"""Merge blocker: a narrativa do relatório não pode divergir de report/significance.csv (Fase 13).

Impede que a "assimetria de significância" (celebrar como vitória/regressão real uma célula que
não passa o teste de Fisher+FDR) volte ao `SECURITY_AUDIT.md` em edições futuras. Três checagens:

1. **Tabela §4.1** — cada linha da tabela de significância no relatório (célula + flag ✅/❌) deve
   bater com a coluna `significant_fdr` de `report/significance.csv`.
2. **CSV de findings** — `report/security_audit_findings.csv` (coluna `significant_fdr`) deve bater
   com `report/significance.csv`, célula a célula.
3. **Guarda de prosa** — nenhuma célula NÃO-significativa pode aparecer enquadrada como
   *significativa* (sem negação por perto). E a(s) célula(s) significativa(s) deve(m) ser
   descrita(s) como tal pelo menos uma vez.

Exit 0 se tudo consistente; 1 com a lista de divergências.

Uso:  python scripts/check_significance_consistency.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "report"
SIG_PATH = REPORT_DIR / "significance.csv"
FINDINGS_PATH = REPORT_DIR / "security_audit_findings.csv"
AUDIT_PATH = REPORT_DIR / "SECURITY_AUDIT.md"

# Negação / marcador de não-significância na mesma linha desarma a frase como "claim de vitória".
_NEG_TOKENS = (
    "não",
    "nao",
    "n.s.",
    "ruído",
    "ruido",
    "q=1",
    "q≥",
    "q >=",
    "não-signific",
    "aparente",
)
# Linha que afirma significância de uma célula.
_SIG_WORD = re.compile(r"significativ", re.IGNORECASE)
_CELL_RE = re.compile(r"`([abc]_[a-z_]+)`")


def load_significance() -> dict[str, bool]:
    if not SIG_PATH.exists():
        print(
            f"ERRO: {SIG_PATH} não existe. Rode scripts/compute_significance.py.", file=sys.stderr
        )
        raise SystemExit(1)
    s = pd.read_csv(SIG_PATH)
    return dict(zip(s["finding_id"], s["significant_fdr"].astype(bool)))


def check_table(text: str, sig: dict[str, bool]) -> list[str]:
    """Cada linha da tabela §4.1 (`cell` ... ✅/❌) bate com significance.csv."""
    errors = []
    for line in text.splitlines():
        if not line.lstrip().startswith("| `"):
            continue
        if "✅" not in line and "❌" not in line:
            continue
        m = _CELL_RE.search(line)
        if not m:
            continue
        cell = m.group(1)
        if cell not in sig:
            continue
        claims_sig = "✅" in line
        if claims_sig != sig[cell]:
            errors.append(
                f"§4.1 tabela: `{cell}` marcada {'✅ significativa' if claims_sig else '❌ não'} "
                f"mas significance.csv diz significant_fdr={sig[cell]}"
            )
    return errors


def check_findings_csv(sig: dict[str, bool]) -> list[str]:
    if not FINDINGS_PATH.exists():
        return [f"{FINDINGS_PATH.name} não existe"]
    f = pd.read_csv(FINDINGS_PATH)
    if "significant_fdr" not in f.columns:
        return [f"{FINDINGS_PATH.name} sem coluna significant_fdr"]
    errors = []
    for _, r in f.iterrows():
        cell = r["finding_id"]
        if cell in sig and bool(r["significant_fdr"]) != sig[cell]:
            errors.append(
                f"findings.csv: `{cell}` significant_fdr={bool(r['significant_fdr'])} "
                f"!= significance.csv {sig[cell]}"
            )
    return errors


def check_prose(text: str, sig: dict[str, bool]) -> list[str]:
    """Nenhuma célula não-significativa enquadrada como *significativa* sem negação por perto.

    Usa janela de proximidade (±35 chars em torno da menção da célula) para evitar falso-positivo
    quando a célula não-significativa apenas coexiste na linha com outra que é significativa.
    """
    errors = []
    non_sig = {c for c, v in sig.items() if not v}
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("| "):  # tabelas tratadas em check_table
            continue
        for m in _CELL_RE.finditer(line):
            cell = m.group(1)
            if cell not in non_sig:
                continue
            window = line[max(0, m.start() - 35) : m.end() + 35].lower()
            if _SIG_WORD.search(window) and not any(tok in window for tok in _NEG_TOKENS):
                errors.append(
                    f"L{i}: `{cell}` (não-significativa) junto de «significativ» sem negação: "
                    f"«{line.strip()[:100]}»"
                )
    return errors


def check_significant_described(text: str, sig: dict[str, bool]) -> list[str]:
    """Cada célula significativa deve ser descrita como tal ao menos uma vez (fora de tabela)."""
    significant = [c for c, v in sig.items() if v]
    errors = []
    for cell in significant:
        described = False
        for line in text.splitlines():
            if line.lstrip().startswith("| "):
                continue
            low = line.lower()
            if (
                f"`{cell}`" in line
                and _SIG_WORD.search(line)
                and not any(t in low for t in ("não", "nao", "não-signific"))
            ):
                described = True
                break
        if not described:
            errors.append(
                f"célula significativa `{cell}` não é descrita como significativa na prosa"
            )
    return errors


def main() -> int:
    if not AUDIT_PATH.exists():
        print(f"ERRO: {AUDIT_PATH} não existe.", file=sys.stderr)
        return 1
    sig = load_significance()
    text = AUDIT_PATH.read_text(encoding="utf-8")

    errors = (
        check_table(text, sig)
        + check_findings_csv(sig)
        + check_prose(text, sig)
        + check_significant_described(text, sig)
    )

    n_sig = sum(1 for v in sig.values() if v)
    print(f"significance.csv: {len(sig)} células, {n_sig} significativa(s) (q<0,05).")
    if errors:
        print(f"\nFALHA — {len(errors)} divergência(s) narrativa↔significância:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK — relatório, findings.csv e tabela §4.1 consistentes com significance.csv.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
