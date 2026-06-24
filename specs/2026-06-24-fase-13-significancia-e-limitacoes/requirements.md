# Requirements — Fase 13: Significância estatística e calibração de limitações

## Scope

### In scope
- **P0 — Destravar dados:** `report/audit_counts.csv` versionado (21 linhas, inteiros) gerado pelo
  notebook 00 a partir do `evidence/` local; `statsmodels` adicionado ao `pyproject.toml`.
- **Bloco 1 — Significância:** `scripts/compute_significance.py` (Fisher exato por célula + FDR
  Benjamini-Hochberg) gerando `report/significance.csv` com `p_value`, `q_value`, `significant_fdr`.
- **Bloco 2 — Narrativa:** reescrita do `SECURITY_AUDIT.md` para que toda alegação de redução/regressão
  concorde com `significant_fdr`; coluna `q_value`/flag na tabela da §4.1.
- **Bloco 3 — Reescopar (decisão B):** Cenário 3 recalibrado como prova de existência / estudo de caso
  em §3, §6.2, `threat_model.md` §6.3 e abstract.
- **Bloco 4 — Rigor:** kappa de Cohen (heurística-vs-manual, 10%), n assimétrico de `model_theft`
  documentado, `residual_asr := asr_base` explicitado, caveat de reprodutibilidade no `tech-stack.md`,
  `priority` declarado como ranking ad-hoc.
- **Bloco 5 — Docs + checks:** `LIMITATIONS.md` (raiz), `docs/EVALUATION.md`, `CONTRIBUTING.md` (raiz),
  3 templates de issue em `.github/ISSUE_TEMPLATE/`; `scripts/check_significance_consistency.py` como
  merge blocker; regeneração determinística via `make report`.

### Out of scope
- **Medir a bateria do Cenário 3** (LIMITATIONS item 3, opção A) — adiado para Trilha 2 L2 (red-team),
  por decisão ratificada e pela regra de ouro do EVALUATION (não abrir Trilha 2 antes da Trilha 1 L1).
- **Aumentar n** das células decisivas (LIMITATIONS item 4b) — exige nova coleta com API; fora desta fase.
- **Trilhas 2, 3 (L1+), 4** do EVALUATION — só após o merge desta revisão.
- **arXiv / Zenodo / CITATION.cff** (Trilha 1 L2) — fase posterior.
- Reexecução ao vivo da matriz contra LLMs — a fonte desta fase é a contagem commitada, não chamadas de API.

## Key Decisions

| Decisão | Escolha | Rationale |
|---|---|---|
| Achado central (Bloco 3) | **(B) Reescopar** | Cenário 3 vira estudo de caso/prova de existência; medir a taxa é trabalho de Trilha 2, que o EVALUATION posiciona depois da correção de significância. |
| Docs de revisão no repo | **Incluir nesta fase** | São pré-requisitos L0 das Trilhas 1/2/3; já corrigidos na pasta Revisoes. |
| Idioma dos artefatos | **Bilíngue** | `CONTRIBUTING.md` + templates em EN (interface do contribuidor, convenção GitHub); `LIMITATIONS.md` + `EVALUATION.md` + relatório em PT. |
| `check_significance_consistency.py` | **Merge blocker obrigatório** | Impede a assimetria de significância de retornar no futuro; gate em CI + `report-check`. |
| Teste estatístico por célula | **Fisher exato (two-sided)** | n pequeno (60–121) inviabiliza aproximações normais; substitui o "olhômetro de sobreposição de IC". |
| Correção de múltiplas comparações | **Benjamini-Hochberg (FDR)** | 21 testes simultâneos; controla a taxa de falsos-positivos sem o conservadorismo de Bonferroni. |
| Limiar de significância | **q < 0,05** | Padrão; aplicado sobre q-values pós-FDR, não p-values brutos. |

## Context

### Mission alignment
A missão exige "evidência quantitativa" e "reprodutibilidade" como princípios. Esta fase corrige a
maior fraqueza metodológica do entregável (tratamento assimétrico de significância) e destrava a
reprodução sem-API (CSV de contagens commitado), elevando o rigor ao nível esperado de uma auditoria
"executive-ready" e citável.

### Tech-stack alignment
- Usa a camada de avaliação já existente (Pandas, Jupyter, notebook 00) e o `scipy>=1.13` já fixado;
  adiciona apenas `statsmodels` ao grupo `redteam`.
- Respeita ADR-002: a fonte de verdade do runtime é o `.env` (Together AI / Llama 3.3 70B / Guard 4);
  o caveat de reprodutibilidade (Bloco 4) registra a string exata de modelo + data do run.
- Mantém o caveat metodológico de `model_theft` (rate limiting = controle de volume, ASR NÃO-APLICÁVEL).

### Dependencies
- Depende do `evidence/` local (gitignored) **uma única vez**, em P0, para gerar `audit_counts.csv`.
  Após isso, toda a cadeia de análise roda sobre os CSVs commitados.
- Depende dos artefatos das Fases 9–11: `security_audit_matrix.csv`, `security_audit_findings.csv`,
  `SECURITY_AUDIT.md`, `threat_model.md`, notebook `00_audit_report.ipynb`, alvos `make report*`.
