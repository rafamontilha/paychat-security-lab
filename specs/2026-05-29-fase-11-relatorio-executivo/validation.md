# Validation — Fase 11: Relatório Executivo

Os quatro critérios abaixo foram marcados como **obrigatórios** (bloqueiam o merge):
notebook 00 headless, cobertura 21/21, PDF sem erro e revisão de leitura.

## Automated checks

- [ ] [auto] `jupyter nbconvert --to notebook --execute --inplace notebooks/00_audit_report.ipynb`
      (kernel do `.venv`) executa de ponta a ponta sem erro e regenera todas as figuras em
      `report/figures/` lidas dos CSVs de evidência
- [ ] [auto] `python scripts/check_audit_coverage.py` reporta **21/21** células da matriz 3×7 com
      finding/entrada correspondente no `report/SECURITY_AUDIT.md` (exit 0; falha lista as ausentes)
- [ ] [auto] `make report-pdf` gera `report/SECURITY_AUDIT.pdf` sem erro de build (exit 0)
- [ ] [auto] `grep -c "NÃO-APLICÁVEL\|NAO-APLICAVEL" report/SECURITY_AUDIT.md` confirma o caveat de
      `model_theft` presente (count ≥ 1)
- [ ] [auto] Verificação de figuras órfãs: toda figura referenciada no `SECURITY_AUDIT.md` existe em
      `report/figures/` (sem links quebrados) — checagem incluída no `check_audit_coverage.py`
- [ ] [auto] CI verde: `ruff`, `black`, `mypy` passando sobre o código novo (Makefile, script de
      cobertura, helpers do notebook)

## Manual smoke tests

- [ ] [manual] Abrir `report/SECURITY_AUDIT.pdf` e confirmar: sumário navegável, heatmaps e curvas
      embutidos e legíveis, diagrama da Variante C renderizado, sem páginas em branco/figuras cortadas
- [ ] [manual] Abrir `report/SECURITY_AUDIT.md` no GitHub (pré-push): tabelas renderizam sem quebra,
      imagens carregam via caminho relativo, link para `report/threat_model.md` funciona
- [ ] [manual] Ler executive summary → apêndice técnico de uma vez: um leitor externo (CISO, líder de
      engenharia de payments) navega das recomendações aos detalhes sem consultar outro documento
- [ ] [manual] Conferir na matriz e nos findings que `model_theft` aparece como **NÃO-APLICÁVEL**
      (não como "redução %"), com a justificativa metodológica (volume vs conteúdo)
- [ ] [manual] Conferir que as Variantes B/C são descritas como **Llama 3.3 70B Turbo via Together AI**
      (ADR-002) e que o Llama Guard 4 é descrito como **dependente de categoria** — sem a afirmação
      falsa de que "o guard não detecta injeção"
- [ ] [manual] Amostrar 5 afirmações quantitativas do relatório e confirmar que cada uma referencia
      evidência (`evidence/...`, célula da matriz ou figura do notebook 00)

## Merge blockers

O PR não deve ser mergeado enquanto qualquer um dos itens abaixo for falso:

1. `report/SECURITY_AUDIT.md` existe e contém todas as seções do roadmap: executive summary,
   contexto e escopo, threat model resumido (com link), matriz 3×7 baseline vs pós-defesa,
   análise arquitetural A/B/C, findings por categoria, risco residual por arquitetura,
   remediações priorizadas, apêndice técnico
2. `notebooks/00_audit_report.ipynb` executa headless via `nbconvert` sem erro e é a fonte de
   todas as figuras em `report/figures/` (regeneradas dos CSVs, não copiadas manualmente)
3. `scripts/check_audit_coverage.py` executa sem erro e reporta 21/21 células cobertas, sem
   figuras órfãs
4. `make report-pdf` gera `report/SECURITY_AUDIT.pdf` navegável, com sumário e figuras embutidas
5. `model_theft` está marcado NÃO-APLICÁVEL (sem redução %), consistente com mission v4 e o caveat
   metodológico da Fase 9
6. Rótulos de runtime corretos: B/C = Llama 3.3 70B Turbo via Together AI (ADR-002); Llama Guard 4
   descrito como dependente de categoria
7. CI verde (lint + format + type check) sobre o código novo
8. Revisão de leitura humana concluída (confirmada pelo autor na descrição do PR)
9. `CHANGELOG.md` atualizado com a entrada da Fase 11
