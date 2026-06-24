# Plan — Fase 13: Significância estatística e calibração de limitações

> Revisão metodológica pós-v1.0.0 (Trilha 1 do `docs/EVALUATION.md`). Resolve os
> bloqueadores `[BLOQUEADOR-ARXIV]` do `LIMITATIONS.md` (itens 1, 2, 3) e os itens de
> rigor 4–8, antes de expor o projeto a avaliação adversarial externa.
>
> **Ordem dos blocos:** P0 → Bloco 1 → Bloco 2 são bloqueadores e vêm primeiro. Bloco 3
> (reescopar) pode correr em paralelo. Bloco 4 depois. Bloco 5 fecha. PR só depois do Bloco 5.

## 0. P0 — Destravar dados e ambiente (pré-requisito de tudo)
- [ ] Confirmar branch `revisao/significancia-e-limitacoes` (já criada).
- [ ] Adicionar `statsmodels` ao grupo `redteam` do `pyproject.toml` (junto de `scipy>=1.13`).
- [ ] Rodar o install do projeto (uv sync com extras `redteam`) e validar import de `statsmodels` + `scipy`.
- [ ] Em `notebooks/00_audit_report.ipynb`, adicionar célula que lê o `evidence/` local e escreve
      `report/audit_counts.csv` com colunas: `finding_id, variant, category, succ_base, n_base, succ_post, n_post`.
- [ ] Commitar `report/audit_counts.csv` (contagens agregadas, não payloads — seguro de publicar).
- [ ] **Conferência:** CSV com 21 linhas, valores inteiros; `succ_base/n_base` bate com `asr_base`
      de `report/security_audit_matrix.csv` dentro do arredondamento.

## 1. Bloco 1 — Significância por célula + FDR (LIMITATIONS itens 1 e 2)
- [ ] Criar `scripts/compute_significance.py`: lê `audit_counts.csv`, monta tabela 2×2 por célula
      `[[succ_base, n_base-succ_base],[succ_post, n_post-succ_post]]`.
- [ ] Calcular `p_value` por célula com **Fisher exato** (`scipy.stats.fisher_exact`, two-sided).
- [ ] Calcular `q_value` com **Benjamini-Hochberg** (`statsmodels.stats.multitest.multipletests`, `method="fdr_bh"`).
- [ ] Derivar `significant_fdr = q_value < 0.05`.
- [ ] Escrever `report/significance.csv` (21 linhas) e imprimir tabela formatada para colar no relatório.
- [ ] **Conferência:** listar exatamente quais células têm `significant_fdr=True`. Expectativa da
      revisão: `b_pi_direct` passa; `c_sensitive_disclosure`, `b_ioh` e as "regressões" provavelmente
      não passam — confirmar com os números reais.

## 2. Bloco 2 — Reescrever a narrativa para bater com o teste (LIMITATIONS item 1, textual)
- [ ] Percorrer `report/SECURITY_AUDIT.md`: toda frase de "redução X%", "melhor célula", "regressão".
- [ ] Onde `significant_fdr=False`: rebaixar para "variação dentro do ruído (q>0,05, n pequeno)".
- [ ] Manter linguagem de vitória causal **só** onde `significant_fdr=True` (hoje: `b_pi_direct` é a única inequívoca).
- [ ] Incluir coluna `q_value` + flag de significância na tabela da §4.1.
- [ ] **Conferência:** cada alegação de redução/regressão mapeia para a flag; nenhuma célula
      não-significativa mantém enquadramento de "vitória" ou "piora real".

## 3. Bloco 3 — Achado central: REESCOPAR (decisão B ratificada) (LIMITATIONS item 3)
- [ ] Editar o relatório para chamar o **Cenário 3** de *prova de existência / estudo de caso*.
- [ ] Calibrar a linguagem ("demonstramos ser possível", não "é o regime geral") de forma consistente em:
      `SECURITY_AUDIT.md` §3, §6.2; `report/threat_model.md` §6.3; e o abstract.
- [ ] **Não** construir bateria de payloads (isso é Trilha 2 L2, posterior — regra de ouro do EVALUATION).
- [ ] **Conferência:** linguagem da tese de não-comutatividade calibrada e consistente em todos os lugares.

## 4. Bloco 4 — Qualidade de dados e documentação (LIMITATIONS itens 4–7)
- [ ] **Kappa de Cohen** heurística-vs-manual sobre a amostra de 10%, reportado por categoria
      (§2.2 ou apêndice).
- [ ] Documentar (relatório + CSV) o **n assimétrico** de `model_theft` (a=79 vs b/c=121) e por quê.
- [ ] Documentar a definição `residual_asr := asr_base` para model_theft (controle de volume, §4.3) —
      nota inline na coluna ou no schema do `security_audit_findings.csv`.
- [ ] Caveat de reprodutibilidade: registrar string exata de modelo + data do run em `specs/tech-stack.md`;
      afirmar critério "dentro do IC95%".
- [ ] Uma frase na §8 declarando `priority = cvss_env × residual_asr` como **ranking ad-hoc**, não métrica CVSS padrão.
- [ ] **Conferência:** os quatro itens aparecem no relatório; nenhuma coluna fica sem definição.

## 5. Bloco 5 — Docs de revisão, checks finais e novo merge blocker
### 5a. Docs de revisão (decisão "incluir" ratificada — bilíngue)
- [ ] Adicionar `LIMITATIONS.md` (raiz, PT) a partir da pasta Revisoes.
- [ ] Adicionar `docs/EVALUATION.md` (PT) a partir da pasta Revisoes.
- [ ] Adicionar `CONTRIBUTING.md` (raiz, EN) a partir da pasta Revisoes.
- [ ] Adicionar `.github/ISSUE_TEMPLATE/{methodology_critique,red_team_break,reproduction_report}.md` (EN).
### 5b. Novo merge blocker (decisão "gate obrigatório" ratificada)
- [ ] Criar `scripts/check_significance_consistency.py`: falha (exit 1) se alguma alegação de
      redução/regressão no `SECURITY_AUDIT.md` divergir de `report/significance.csv`.
- [ ] Integrar ao CI (GitHub Actions) e/ou ao alvo `report-check` como gate.
### 5c. Regeneração e consistência
- [ ] `make report` regenera figuras, PDF e roda o check — sai com código 0.
- [ ] `python scripts/check_audit_coverage.py` → 21/21 e zero figura quebrada.
- [ ] Re-rodar o notebook 00 ponta a ponta sobre os CSVs commitados; confirmar que
      `security_audit_{matrix,findings}.csv` regeneram de forma determinística (agora possível,
      pois a fonte é contagem commitada, não chamada de LLM).
- [ ] **Conferência:** `make report` exit 0; cobertura 21/21; check de consistência passa;
      `git diff` mostra só as mudanças pretendidas.

## 6. Fechamento
- [ ] Abrir o PR `revisao/significancia-e-limitacoes` → `main`.
- [ ] Só após o merge, mover para a Trilha 2 (red-team) do `docs/EVALUATION.md`.
