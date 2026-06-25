# Validation — Fase 13: Significância estatística e calibração de limitações

## Automated checks
- [ ] [auto] `python scripts/compute_significance.py` gera `report/significance.csv` com 21 linhas e
      as colunas `finding_id, variant, category, p_value, q_value, significant_fdr`.
- [ ] [auto] `python scripts/check_significance_consistency.py` sai com código 0 — nenhuma alegação de
      redução/regressão no `SECURITY_AUDIT.md` diverge de `report/significance.csv` (**merge blocker**).
- [ ] [auto] `python scripts/check_audit_coverage.py` reporta 21/21 células e zero figura quebrada.
- [ ] [auto] `make report` (report-figures → report-pdf → report-check) sai com código 0.
- [ ] [auto] Import de `statsmodels` e `scipy` funciona no ambiente após o install (grupo `redteam`).
- [ ] [auto] CI (GitHub Actions) executa o novo `check_significance_consistency.py` e falha o PR se divergir.

## Manual smoke tests
- [ ] [manual] Abrir `report/audit_counts.csv`: 21 linhas, todos os valores inteiros; conferir que
      `succ_base/n_base` de pelo menos 3 células bate com `asr_base` da matriz dentro do arredondamento.
- [ ] [manual] Rodar `compute_significance.py` e confirmar à mão a expectativa da revisão:
      `b_pi_direct` com `significant_fdr=True`; `c_sensitive_disclosure`, `b_ioh` e as regressões
      (`b_sensitive_disclosure`, `c_excessive_agency`, `a_insecure_plugin`) com `significant_fdr=False`.
- [ ] [manual] Ler a §4.1 do `SECURITY_AUDIT.md`: a coluna `q_value`/flag está presente e cada linha
      de redução/regressão usa linguagem coerente com a flag (vitória causal só onde True; "dentro do
      ruído" onde False).
- [ ] [manual] Buscar no relatório, threat_model §6.3 e abstract pela tese de não-comutatividade:
      toda menção ao Cenário 3 está calibrada como prova de existência / estudo de caso (decisão B).
- [ ] [manual] Confirmar presença e idioma dos docs: `LIMITATIONS.md` (PT, raiz), `docs/EVALUATION.md`
      (PT), `CONTRIBUTING.md` (EN, raiz), 3 templates EN em `.github/ISSUE_TEMPLATE/`.
- [ ] [manual] Re-rodar o notebook 00 ponta a ponta sobre os CSVs commitados e confirmar que
      `security_audit_{matrix,findings}.csv` regeneram identicamente (determinismo sem chamada de LLM).

## Merge blockers

O PR não pode ser mergeado a menos que TODAS as condições abaixo sejam verdadeiras:
1. `report/audit_counts.csv` commitado: 21 linhas, inteiros, consistente com `asr_base` da matriz.
2. `report/significance.csv` gerado com `p_value`, `q_value`, `significant_fdr` para as 21 células.
3. Nenhuma alegação de redução/regressão no `SECURITY_AUDIT.md` contradiz `significance.csv`
   (verificado por `scripts/check_significance_consistency.py`, exit 0).
4. Cenário 3 recalibrado como prova de existência em §3, §6.2, threat_model §6.3 e abstract (decisão B).
5. Itens de rigor 4–7 do `LIMITATIONS.md` endereçados no relatório (kappa, n assimétrico, `residual_asr`,
   caveat de reprodutibilidade, `priority` ad-hoc) — nenhuma coluna sem definição.
6. Docs de revisão versionados no idioma correto (bilíngue) nos caminhos esperados.
7. `make report` exit 0 e `check_audit_coverage.py` 21/21.
8. `git diff` mostra apenas as mudanças pretendidas (sem payloads brutos de `evidence/` vazando).
