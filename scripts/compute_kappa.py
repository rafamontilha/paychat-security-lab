"""Concordância heurística-vs-manual (kappa de Cohen) sobre a amostra de 10% (Fase 13).

Resolve o item 5 do `LIMITATIONS.md`: o `success_flag` vem de uma heurística por categoria;
sua precisão vs. ground-truth manual não estava quantificada. Este script materializa o
fluxo de revisão humana descrito em `red_team/README.md` §9 de forma reproduzível.

Dois modos:

  python scripts/compute_kappa.py --build      # gera a amostra estratificada (10%) vazia
  python scripts/compute_kappa.py              # computa kappa por categoria do CSV preenchido

A amostra é estratificada por (variant, category, temperature) com piso de 5 por estrato
(mesma regra de notebooks/01), random_state=42 (reproduzível). Por padrão cobre as 3
categorias com gate de kappa (pi_direct, pi_indirect, ioh); use --all para as 7.

O CSV vive em `evidence/baseline/manual_review_sample.csv` (gitignored: contém payloads e
responses brutos). **Só os valores de kappa entram no relatório**, nunca o conteúdo bruto.

Preenchimento: na coluna `manual_review`, marque para cada linha se o ataque **de fato**
teve sucesso — `True`/`False` (ou 1/0). Depois rode o modo de cálculo.

Kappa de Cohen é calculado sem dependências externas (po, pe binários).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = ROOT / "evidence" / "baseline"
SAMPLE_PATH = EVIDENCE_DIR / "manual_review_sample.csv"

GATE_CATEGORIES = ["pi_direct", "pi_indirect", "ioh"]
SAMPLE_COLS = [
    "id",
    "variant",
    "category",
    "temperature",
    "technique",
    "payload",
    "response",
    "success_flag",
    "success_reason",
    "manual_review",
]
RANDOM_STATE = 42


def _load_baseline() -> pd.DataFrame:
    rows = []
    for f in EVIDENCE_DIR.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("execution_status") == "success":
            rows.append(d)
    if not rows:
        print(
            f"ERRO: nenhuma evidência em {EVIDENCE_DIR}. O evidence/ é gitignored; "
            "rode a coleta (README) antes de gerar a amostra.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return pd.DataFrame(rows)


def build(all_categories: bool) -> int:
    df = _load_baseline()
    if not all_categories:
        df = df[df["category"].isin(GATE_CATEGORIES)]

    frames = []
    for _, g in df.groupby(["variant", "category", "temperature"]):
        n_sample = min(max(5, int(len(g) * 0.10)), len(g))
        frames.append(g.sample(n=n_sample, random_state=RANDOM_STATE))
    sample = pd.concat(frames).reset_index(drop=True)
    sample["manual_review"] = pd.NA
    for col in SAMPLE_COLS:
        if col not in sample.columns:
            sample[col] = pd.NA
    sample[SAMPLE_COLS].to_csv(SAMPLE_PATH, index=False)

    scope = (
        "7 categorias" if all_categories else "3 categorias com gate (pi_direct, pi_indirect, ioh)"
    )
    print(f"Amostra gerada: {SAMPLE_PATH}")
    print(f"  {len(sample)} registros · {scope}")
    print(f"  por categoria: {sample['category'].value_counts().to_dict()}")
    print(
        "\nPreencha a coluna `manual_review` (True/False) e rode: python scripts/compute_kappa.py"
    )
    return 0


def cohen_kappa(rater_a: pd.Series, rater_b: pd.Series) -> float:
    """Kappa de Cohen para dois raters binários, sem dependências externas."""
    a = rater_a.astype(int).to_numpy()
    b = rater_b.astype(int).to_numpy()
    po = (a == b).mean()
    # Probabilidade de concordância esperada por acaso.
    pe = sum((((a == k).mean()) * ((b == k).mean())) for k in (0, 1))
    if pe >= 1.0:  # ambos raters constantes e idênticos -> concordância perfeita trivial
        return 1.0 if po == 1.0 else 0.0
    return float((po - pe) / (1 - pe))


def _to_bool(s: pd.Series) -> pd.Series:
    # Normaliza para string minúscula antes de mapear: cobre bool True/False (lidos do CSV),
    # "True"/"true", "1"/"0", "1.0"/"0.0" e sim/não, sem colisão de chaves bool-vs-int.
    norm = s.astype(str).str.strip().str.lower()
    return norm.map(
        {"true": 1, "false": 0, "1": 1, "0": 0, "1.0": 1, "0.0": 0, "sim": 1, "nao": 0, "não": 0}
    )


def compute() -> int:
    if not SAMPLE_PATH.exists():
        print(
            f"ERRO: {SAMPLE_PATH} não existe. Gere a amostra primeiro: "
            "python scripts/compute_kappa.py --build",
            file=sys.stderr,
        )
        raise SystemExit(1)

    m = pd.read_csv(SAMPLE_PATH)
    m = m[m["manual_review"].notna()].copy()
    if m.empty:
        print(
            "ERRO: coluna `manual_review` vazia. Preencha True/False e rode de novo.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    m["manual_bin"] = _to_bool(m["manual_review"])
    m["heur_bin"] = _to_bool(m["success_flag"])
    bad = m[m["manual_bin"].isna()]
    if not bad.empty:
        vals = bad["manual_review"].unique()
        print(
            f"ERRO: valores não reconhecidos em manual_review (use True/False): {vals}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(f"Concordância heurística-vs-manual (kappa de Cohen) · n avaliado = {len(m)}\n")
    print(f"{'categoria':<24}{'n':>4}{'kappa':>8}{'concord.%':>11}  status")
    summary = []
    for cat, grp in m.groupby("category"):
        if len(grp) < 2:
            continue
        k = cohen_kappa(grp["heur_bin"], grp["manual_bin"])
        agree = (grp["heur_bin"] == grp["manual_bin"]).mean() * 100
        status = "OK (>=0,6)" if k >= 0.6 else "ABAIXO DO LIMIAR — revisar heurística"
        print(f"{cat:<24}{len(grp):>4}{k:>8.3f}{agree:>10.1f}%  {status}")
        summary.append(
            {"category": cat, "n": len(grp), "kappa": round(k, 3), "agreement_pct": round(agree, 1)}
        )

    k_all = cohen_kappa(m["heur_bin"], m["manual_bin"])
    agree_all = (m["heur_bin"] == m["manual_bin"]).mean() * 100
    print(f"{'GERAL':<24}{len(m):>4}{k_all:>8.3f}{agree_all:>10.1f}%")

    out = ROOT / "report" / "kappa_summary.csv"
    pd.DataFrame(
        summary
        + [
            {
                "category": "GERAL",
                "n": len(m),
                "kappa": round(k_all, 3),
                "agreement_pct": round(agree_all, 1),
            }
        ]
    ).to_csv(out, index=False)
    print(f"\nsaved: {out}  (seguro de publicar — só métricas de concordância, sem payloads)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Kappa de Cohen heurística-vs-manual (Fase 13).")
    ap.add_argument("--build", action="store_true", help="gera a amostra estratificada vazia")
    ap.add_argument(
        "--all",
        action="store_true",
        help="com --build: cobre as 7 categorias (default: 3 com gate)",
    )
    args = ap.parse_args()
    return build(args.all) if args.build else compute()


if __name__ == "__main__":
    sys.exit(main())
