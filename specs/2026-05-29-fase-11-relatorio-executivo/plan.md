# Plan — Fase 11: Relatório Executivo

Ordem de construção escolhida: **notebook-first**. O `notebooks/00_audit_report.ipynb` é a
**fonte única** das visualizações — regenera todas as figuras a partir dos CSVs de evidência;
o `report/SECURITY_AUDIT.md` consome essas figuras; só então geramos o PDF e revisamos.

> Estado de partida: `report/SECURITY_AUDIT.md` é stub de 1 linha; `notebooks/00_audit_report.ipynb`
> está vazio (0 células). `report/threat_model.md` (Fase 10) está completo — o relatório **resume e
> linka**, não duplica. Dados prontos: `evidence/baseline/summary.csv`,
> `evidence/post_defense/reduction_summary.csv`, figuras em `evidence/{baseline,post_defense,whitebox}/figures/`.

## 1. Notebook 00 como fonte única das visualizações
- [ ] Auditar artefatos de dados existentes: `evidence/baseline/summary.csv`,
      `evidence/post_defense/reduction_summary.csv`, `evidence/whitebox/figures/roc_curve.png`
- [ ] Construir `notebooks/00_audit_report.ipynb` lendo evidências **direto do disco**
      (baseline + post_defense), nunca por re-execução de ataque ao vivo
- [ ] Regenerar **todas** as figuras do relatório a partir dos CSVs num diretório canônico
      (`report/figures/`): heatmap 3×7 baseline, heatmap de redução %, ASR por categoria,
      curva de loss do GCG, curva ROC do MIA
- [ ] Tabela mestre: matriz 3×7 baseline vs pós-defesa com ASR + IC95% (Wilson) por célula
- [ ] Coluna `block_rate_post` (guard/defense) para revelar o bônus do Llama Guard 4
      (pi_direct C ≈ 92%, sensitive_disclosure C ≈ 50%, excessive_agency C ≈ 55%)
- [ ] `model_theft`: `reduction_pct = NaN` + nota inline **NÃO-APLICÁVEL** (volume, não conteúdo)
- [ ] Célula de ranking dos top-5 findings (ASR baseline × score CVSS do threat_model)
- [ ] Rodar headless via `nbconvert` no kernel do `.venv`; confirmar 0 erros e figuras regeneradas

## 2. Redação do `report/SECURITY_AUDIT.md`
- [ ] Executive summary (≤ 1 página): top-5 findings, redução agregada de risco, recomendações priorizadas
- [ ] Contexto e escopo (puxa de `mission.md`; enuncia as 3 variantes e a matriz 3×7)
- [ ] Threat model resumido — **linka** `report/threat_model.md` (STRIDE, CVSS, cenários compostos), sem duplicar
- [ ] Matriz 3×7 baseline vs pós-defesa: heatmaps embutidos (figuras do notebook 00)
- [ ] Análise arquitetural comparativa A vs B vs C (reusa trade-offs do `threat_model.md` §10)
- [ ] Findings detalhados por categoria (7): causa raiz, evidência referenciada, impacto, remediação
- [ ] Risco residual quantificado por arquitetura (consome matriz CVSS Environmental do threat_model)
- [ ] Remediações priorizadas (CVSS + impacto de negócio: account takeover, vendor impersonation, chargeback)
- [ ] Apêndice técnico: catálogo de técnicas, white-box GPT-2 (GCG + MIA), decisões arquiteturais (ADR-001/002)

## 3. Toolchain de PDF (Pandoc + Makefile)
- [ ] Instalar Pandoc + engine PDF no host (LaTeX via MiKTeX **ou** wkhtmltopdf — o que gerar limpo no Windows)
- [ ] Criar `Makefile` com alvo `report-pdf` (e `report-figures` que dispara o `nbconvert` do notebook 00)
- [ ] Resolver embedding de figuras (PNG) e do SVG do diagrama (`report/assets/variante_c_flow.svg`)
- [ ] Gerar `report/SECURITY_AUDIT.pdf` com sumário e figuras embutidas; validar build sem erro

## 4. Rastreabilidade e cobertura 21/21
- [ ] Garantir que cada uma das 21 células da matriz 3×7 tem finding/entrada correspondente no relatório
- [ ] Script `scripts/check_audit_coverage.py` (novo ou estendendo `check_threat_model_coverage.py`):
      falha listando células sem finding; passa com 21/21 (exit 0)
- [ ] Cross-check: cada afirmação quantitativa do relatório referencia evidência (`evidence/...` ou figura)

## 5. Revisão final e consistência
- [ ] Honrar caveats não-negociáveis: `model_theft` NÃO-APLICÁVEL; runtime real por **ADR-002**
      (B/C = Llama 3.3 70B Turbo via Together AI — "Llama 3.1 8B / Groq" é label histórico);
      Llama Guard 4 é **dependente de categoria** (não escrever "guard não detecta injeção")
- [ ] Leitura completa: do executive summary aos detalhes técnicos sem ambiguidade
- [ ] CI verde (`ruff`, `black`, `mypy`) sobre o código novo (Makefile, script de cobertura, helpers do notebook)
- [ ] Atualizar `CHANGELOG.md` com a entrada da Fase 11
