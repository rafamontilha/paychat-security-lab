"""Teste de significância por célula da matriz 3×7 + correção FDR (Fase 13).

Resolve os bloqueadores metodológicos 1 e 2 do `LIMITATIONS.md`:

1. **Significância por célula** — substitui o "olhômetro de sobreposição de IC95% Wilson"
   (conservador demais) por um **teste exato de Fisher** (two-sided) sobre a tabela 2×2
   baseline↔pós-defesa de cada uma das 21 células. Fisher é apropriado dado o n pequeno
   (60–121) e os baixos contadores de sucesso.

2. **Comparações múltiplas** — aplica **Benjamini-Hochberg (FDR)** sobre o conjunto das 21
   comparações e reporta `q_value`. A 21 testes com α=0,05, ~1 falso-positivo é esperado por
   acaso; o FDR controla isso. A flag de "vitória/regressão real" usa `q_value`, não `p_value`.

Entrada:  report/audit_counts.csv
          (finding_id, variant, category, succ_base, n_base, succ_post, n_post)
Saída:    report/significance.csv
          (+ asr_base, asr_post, delta, direction, p_value, q_value, significant_fdr)

Imprime a tabela formatada (pronta para colar na §4.1 do relatório) e a lista das células
com significant_fdr=True. Exit 0 em sucesso; 1 se a entrada estiver ausente/malformada.

Uso:  python scripts/compute_significance.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy.stats import fisher_exact
from statsmodels.stats.multitest import multipletests

REPORT_DIR = Path(__file__).resolve().parent.parent / "report"
COUNTS_PATH = REPORT_DIR / "audit_counts.csv"
OUT_PATH = REPORT_DIR / "significance.csv"

REQUIRED_COLS = ["finding_id", "variant", "category", "succ_base", "n_base", "succ_post", "n_post"]
ALPHA = 0.05


def p_cell(row: pd.Series) -> float:
    """p-value de Fisher exato (two-sided) para a tabela 2×2 baseline↔pós da célula.

    Tabela: [[sucesso, falha]_base, [sucesso, falha]_post].
    """
    table = [
        [int(row.succ_base), int(row.n_base) - int(row.succ_base)],
        [int(row.succ_post), int(row.n_post) - int(row.succ_post)],
    ]
    return float(fisher_exact(table, alternative="two-sided")[1])


def direction(row: pd.Series) -> str:
    """Sentido da mudança baseline→pós: redução (defesa ajudou), regressão, ou sem mudança."""
    if row.asr_post < row.asr_base:
        return "reducao"
    if row.asr_post > row.asr_base:
        return "regressao"
    return "sem_mudanca"


def load_counts() -> pd.DataFrame:
    if not COUNTS_PATH.exists():
        print(
            f"ERRO: {COUNTS_PATH} não existe. Gere-o primeiro re-executando "
            "notebooks/00_audit_report.ipynb (célula audit_counts) sobre o evidence/ local.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    c = pd.read_csv(COUNTS_PATH)
    missing = [col for col in REQUIRED_COLS if col not in c.columns]
    if missing:
        print(f"ERRO: {COUNTS_PATH.name} sem colunas obrigatórias: {missing}", file=sys.stderr)
        raise SystemExit(1)

    int_cols = ["succ_base", "n_base", "succ_post", "n_post"]
    c[int_cols] = c[int_cols].astype(int)

    bad = c[(c.succ_base > c.n_base) | (c.succ_post > c.n_post) | (c.n_base <= 0) | (c.n_post <= 0)]
    if not bad.empty:
        print(f"ERRO: contagens inválidas (sucesso>n ou n<=0):\n{bad}", file=sys.stderr)
        raise SystemExit(1)

    return c


def compute(c: pd.DataFrame) -> pd.DataFrame:
    c = c.copy()
    c["asr_base"] = (c.succ_base / c.n_base).round(4)
    c["asr_post"] = (c.succ_post / c.n_post).round(4)
    c["delta"] = (c.asr_post - c.asr_base).round(4)
    c["direction"] = c.apply(direction, axis=1)
    c["p_value"] = c.apply(p_cell, axis=1).round(6)
    c["q_value"] = multipletests(c["p_value"], method="fdr_bh")[1].round(6)
    c["significant_fdr"] = c["q_value"] < ALPHA
    return c


def main() -> int:
    c = compute(load_counts())

    cols = [
        "finding_id",
        "variant",
        "category",
        "succ_base",
        "n_base",
        "succ_post",
        "n_post",
        "asr_base",
        "asr_post",
        "delta",
        "direction",
        "p_value",
        "q_value",
        "significant_fdr",
    ]
    c = c[cols].sort_values(["variant", "category"]).reset_index(drop=True)
    c.to_csv(OUT_PATH, index=False)
    print(f"saved: {OUT_PATH} | {len(c)} células\n")

    show = [
        "finding_id",
        "asr_base",
        "asr_post",
        "delta",
        "direction",
        "p_value",
        "q_value",
        "significant_fdr",
    ]
    print(c[show].to_string(index=False))

    sig = c[c.significant_fdr]
    print(f"\nCélulas significativas (q<{ALPHA}, FDR-BH): {len(sig)}/{len(c)}")
    for _, r in sig.iterrows():
        verb = "redução" if r.direction == "reducao" else "regressão"
        print(
            f"  - {r.finding_id}: {verb} {r.asr_base:.4f} -> {r.asr_post:.4f} (q={r.q_value:.4f})"
        )

    nonsig_changes = c[(~c.significant_fdr) & (c.direction != "sem_mudanca")]
    print(
        f"\nMudanças NÃO-significativas (variação dentro do ruído, "
        f"q>={ALPHA}): {len(nonsig_changes)}"
    )
    for _, r in nonsig_changes.iterrows():
        verb = "redução" if r.direction == "reducao" else "regressão"
        print(
            f"  - {r.finding_id}: {verb} aparente "
            f"{r.asr_base:.4f} -> {r.asr_post:.4f} (q={r.q_value:.4f})"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
