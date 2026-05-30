# Requirements — Fase 11: Relatório Executivo

## Scope

### In scope
- `report/SECURITY_AUDIT.md`: relatório de auditoria executivo completo, com as seções:
  executive summary, contexto e escopo, threat model resumido (link), matriz 3×7 baseline vs
  pós-defesa, análise arquitetural A/B/C, findings por categoria, risco residual por arquitetura,
  remediações priorizadas, apêndice técnico
- `notebooks/00_audit_report.ipynb`: notebook consolidado como **fonte única** das visualizações;
  regenera todas as figuras a partir dos CSVs de evidência (baseline + post_defense + white-box)
- `report/figures/`: diretório canônico das figuras geradas pelo notebook 00 e consumidas pelo relatório
- `Makefile` com alvo `report-pdf` (Pandoc) e `report-figures` (nbconvert do notebook 00)
- `report/SECURITY_AUDIT.pdf`: PDF gerado via `make report-pdf`, com sumário e figuras embutidas
- `scripts/check_audit_coverage.py`: valida 21/21 células da matriz 3×7 com finding no relatório
- Entrada da Fase 11 no `CHANGELOG.md`

### Out of scope
- Fase 12 (publicação do repo, LICENSE, tag de release, post no LinkedIn)
- Coleta de novas evidências ou re-execução de ataques (a fase é análise + redação sobre dados já coletados)
- Mapeamento para MITRE ATLAS (Post-MVP no roadmap)
- Re-escrita do `report/threat_model.md` (Fase 10, completo) — o relatório linka e resume, não reescreve
- Score Temporal do CVSS (indisponível para LLMs comerciais — decisão da Fase 10)
- Certificação de compliance formal (PCI-DSS, SOC 2) — entra como recomendação, não entregável

## Key Decisions

| Decisão | Escolha | Rationale |
|---|---|---|
| Ordem de construção | Notebook-first (fonte única) | Figuras regeneradas dos CSVs garantem reprodutibilidade ponta a ponta (merge blocker do roadmap); relatório nunca embute número órfão |
| Toolchain de PDF | Pandoc + `Makefile` (`make report-pdf`) | Atende literalmente o `make report-pdf` do roadmap; Markdown permanece legível no GitHub e diffável |
| Diretório de figuras | `report/figures/` canônico, geradas pelo notebook 00 | Single source of truth; evita divergência entre PNGs dos notebooks 02/03 e o que o relatório mostra |
| Granularidade de findings | 1 finding detalhado por categoria (7) + tabela com as 21 células | Legível para liderança; o detalhe por célula vive na matriz, o narrativo por categoria |
| Relação com threat_model | Resumir + linkar, sem duplicar | Fase 10 já tem STRIDE, CVSS (21 células), cenários compostos, trade-offs e rastreabilidade |
| `model_theft` redução | **NÃO-APLICÁVEL** (sem reduction %) | Rate limiting é controle de volume, não de conteúdo; inflar "redução %" contradiz mission v4 e o caveat metodológico da Fase 9 |
| Rótulo de runtime B/C | Llama 3.3 70B Turbo via Together AI (**ADR-002**) | "Llama 3.1 8B / Groq" é label histórico; o relatório descreve o que executou de fato |
| Caracterização do Llama Guard 4 | Dependente de categoria | Bloqueia onde toca a taxonomia de conteúdo (pi_direct C≈92%, sensitive_disclosure C≈50%); passa em manipulação arquitetural pura (model_theft) — não afirmar "guard não detecta injeção" |
| Cobertura de findings | Script `check_audit_coverage.py` (21/21) | Torna o "done when" mecânico em vez de leitura linha a linha |

## Context

### Mission alignment
A Fase 11 entrega o **relatório de auditoria executivo** — o terceiro pilar do Entregável 3 do
enunciado e o artefato que materializa o critério Distinction: "relatório de auditoria com threat
model, análise multi-model e remediações priorizadas adequadas para revisão executiva". O documento
é redigido para CISO, líderes de engenharia de IA, compliance e engenheiros de plataforma em
payments, separando executive summary do apêndice técnico reprodutível (princípio *executive-ready*
da mission).

### Tech-stack alignment
- **Camada de avaliação:** o notebook 00 consolida Pandas + Matplotlib/Seaborn sobre os CSVs de
  `evidence/baseline/` e `evidence/post_defense/`; nenhum dado novo é gerado.
- **Camada de entrega:** Markdown + Pandoc é a decisão de stack para documentação; o `make report-pdf`
  formaliza a conversão. O SVG do diagrama da Variante C (gerado via `mmdc` na Fase 10) é embutido no PDF.
- **CVSS v3.1:** o risco residual por arquitetura e a priorização de remediações consomem a matriz
  CVSS Environmental já preenchida no `threat_model.md`.

### Dependencies
- **Fase 10 completa:** `report/threat_model.md` (448 linhas) com STRIDE, matriz CVSS 21 células,
  3 cenários compostos, trade-offs A/B/C, mapeamento de impacto de negócio e tabela de rastreabilidade
  (§11) — o relatório linka diretamente esses artefatos
- **Fase 9 completa:** `evidence/post_defense/` (1902 registros, 0 erros), `reduction_summary.csv`
  e `notebooks/03_post_defense.ipynb`; headline pi_direct B = −93,3%, sensitive_disclosure C = −83,3%;
  caveat `model_theft` NÃO-APLICÁVEL registrado
- **Fase 8 completa:** `evidence/baseline/summary.csv`, white-box GPT-2 (GCG + MIA AUC≈0,531,
  `roc_curve.png`) para o apêndice técnico
- **`report/assets/variante_c_flow.svg`** disponível para embutir no PDF
- Toolchain a instalar nesta fase: Pandoc + engine PDF (LaTeX/MiKTeX ou wkhtmltopdf) no host Windows
