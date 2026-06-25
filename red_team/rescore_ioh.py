"""Re-score persisted insecure-output-handling (ioh) evidence with the current heuristic.

Fase 13 corrigiu a heurística de ioh (`evaluate_ioh`): ela agora é *refusal-first* — um agente
que recusa e cita os tokens perigosos do payload deixa de contar como sucesso — e não conta mais
o literal de template injection (`{{7*7}}`) como sucesso. A revisão manual de 10% revelou que a
heurística antiga tinha precisão ~0% em ioh (kappa=0), inflando o ASR (em especial `a_ioh`=67%).

Este script reaplica a heurística canônica às evidências já coletadas, SEM re-chamar nenhum
modelo, para que baseline e pós-defesa usem o mesmo scoring. Só `success_flag`/`success_reason`
são atualizados; response, trace e metadata são preservados. Espelha `red_team/rescore_pi.py`.

Uso:
    python -m red_team.rescore_ioh                          # preview, evidence/baseline
    python -m red_team.rescore_ioh --apply                  # grava
    python -m red_team.rescore_ioh --dir evidence/post_defense --apply
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from red_team.heuristics import evaluate_ioh
from red_team.models import EvidenceRecord


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-score ioh evidence")
    parser.add_argument("--dir", default="evidence/baseline")
    parser.add_argument("--apply", action="store_true", help="write changes (default: preview)")
    args = parser.parse_args()

    evidence_dir = Path(args.dir)
    changed = 0
    total = 0
    flips_to_false = 0
    flips_to_true = 0
    for path in sorted(evidence_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("category") != "ioh":
            continue
        total += 1
        new_flag, new_reason = evaluate_ioh(record.get("response", ""), record.get("trace", []))
        old_flag = bool(record.get("success_flag"))
        if old_flag != new_flag or record.get("success_reason") != new_reason:
            changed += 1
            flips_to_false += 1 if (old_flag and not new_flag) else 0
            flips_to_true += 1 if (not old_flag and new_flag) else 0
            old = f"{record.get('success_flag')}/{record.get('success_reason')}"
            print(f"  {path.name}: {old} -> {new_flag}/{new_reason}")
            if args.apply:
                record["success_flag"] = new_flag
                record["success_reason"] = new_reason
                path.write_text(
                    EvidenceRecord(**record).model_dump_json(indent=2), encoding="utf-8"
                )

    mode = "APPLIED" if args.apply else "PREVIEW (use --apply to write)"
    print(
        f"\n[{mode}] {args.dir}: {changed}/{total} ioh records changed "
        f"(True->False: {flips_to_false}, False->True: {flips_to_true})."
    )


if __name__ == "__main__":
    main()
