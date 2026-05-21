# Validation — Fase 7: Red Team Baseline (PI Direta · PI Indireta · IOH)

## Automated checks

- [ ] [auto] `python red_team/validate_evidence.py` — 0 erros de schema; toda evidência valida contra `EvidenceRecord`
- [ ] [auto] `pytest tests/test_harness_resume.py` — idempotência: rodar harness, interromper no meio, rodar com `--resume`; nenhuma evidência duplicada, nenhuma perdida
- [ ] [auto] `ruff check red_team/` — 0 erros de lint
- [ ] [auto] `black --check red_team/` — 0 erros de formatação
- [ ] [auto] `mypy red_team/` — 0 erros de tipo nos módulos novos

## Manual smoke tests

- [ ] [manual] Dry-run de 30 evidências completa sem erro de execução;
      `evidence/baseline/_dry_run_report.md` gerado com custo Anthropic extrapolado e custo Groq (zero ou mínimo)

- [ ] [manual] Revisão manual 10% estratificada concluída:
      ≥5 evidências por estrato `(variante, célula, temperatura)` revisadas;
      Cohen's kappa calculado e registrado no notebook para cada uma das 3 células

- [ ] [manual] `jupyter nbconvert --to notebook --execute notebooks/01_baseline_pi_ioh.ipynb` executa end-to-end
      lendo apenas arquivos de `evidence/baseline/` (sem chamadas vivas à API);
      heatmaps e CSV gerados sem erro

## Merge blockers

A fase só pode ser mergeada quando **todos** os critérios abaixo são verdadeiros:

1. Matriz 3 variantes × 3 células × 2 temperaturas preenchida com **≥ 45 evidências por estrato** (18 estratos; total ≥ 810 evidências persistidas)
2. 100 % das evidências em `evidence/baseline/` validam contra `EvidenceRecord` Pydantic
3. Taxa de `execution_status=error` **< 5 %** por estrato (re-rodar erros antes do merge; erros não contam para ASR)
4. Cohen's kappa **≥ 0.6** em cada uma das 3 células (PI direta, PI indireta, IOH); se < 0.6, revisar heurística de `success_flag` e recalcular antes de prosseguir
5. Teste `tests/test_harness_resume.py` passa
6. Notebook `notebooks/01_baseline_pi_ioh.ipynb` executa end-to-end a partir de evidências persistidas (sem chamadas à API em execução de CI/notebook)
7. Heatmaps PNG versionados em `evidence/baseline/figures/` (`heatmap_temp_0.0.png`, `heatmap_temp_0.7.png`)
8. `evidence/baseline/summary.csv` gerado com schema estável (colunas: `variant, category, temperature, asr, ci_lower, ci_upper, n_success, n_total`)
9. `evidence/baseline/_dry_run_report.md` documenta custo extrapolado vs custo real ao final
10. Script `red_team/cleanup_poisoned_products.py` existe e foi testado localmente (mas **não executado** — produtos envenenados permanecem para uso na Fase 9)
11. `red_team/README.md` permite reexecução a partir de clone limpo: pré-requisitos, ingestão de produtos, dry-run, execução completa, geração do notebook, wall clock esperado, custo esperado de API
12. CI passa: lint (`ruff`), format (`black`), type check (`mypy`), `validate_evidence.py`
