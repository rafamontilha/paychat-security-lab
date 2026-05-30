# Validation — Fase 10: Threat Model e Análise Arquitetural

## Automated checks

- [ ] [auto] `mmdc -i report/threat_model.md -o report/assets/variante_c_flow.svg` — verifica que
      o diagrama Mermaid é sintaticamente válido e o SVG é gerado sem erro (exit 0)
- [ ] [auto] `python scripts/check_threat_model_coverage.py` — verifica que cada uma das 21 células
      da matriz 3×7 tem entrada correspondente na tabela de rastreabilidade do threat_model.md
      (script a ser criado nesta fase; falha com lista de células ausentes)
- [ ] [auto] `grep -c "NÃO-APLICÁVEL\|NAO-APLICAVEL" report/threat_model.md` — confirma que a nota
      de risco residual qualitativo de model_theft está presente (count ≥ 1)
- [ ] [auto] CI verde: lint (`ruff`), format (`black`), type check (`mypy`) passando após
      qualquer alteração de código introduzida na fase (a fase é primariamente documental,
      mas a correção no tech-stack.md e o script de cobertura são entregáveis de código)

## Manual smoke tests

- [ ] [manual] Abrir `report/threat_model.md` no GitHub (pré-push) e confirmar que:
      (a) o bloco Mermaid renderiza como diagrama — não como bloco de código;
      (b) todas as tabelas renderizam sem quebra de formatação;
      (c) o arquivo SVG em `report/assets/` está commitado e acessível via link relativo
- [ ] [manual] Percorrer a tabela de rastreabilidade linha por linha: para cada uma das 21 células,
      localizar a seção correspondente no STRIDE e o score na matriz CVSS — garantir que os IDs
      de ameaça batem entre os três artefatos (rastreabilidade, STRIDE, CVSS)
- [ ] [manual] Ler a coluna "Risco residual qualitativo" da matriz CVSS: a célula de model_theft
      deve explicar por que o Environmental score não reflete mitigação real, e referenciar o
      caveat registrado no notebook 03 / CHANGELOG da Fase 9
- [ ] [manual] Ler os 3 cenários compostos e confirmar que o Cenário 3 (falha composta) identifica
      claramente *por que* a composição cria a brecha — não apenas *o que* acontece
- [ ] [manual] Revisão de leitura completa do `report/threat_model.md`: um leitor externo (CISO,
      líder de engenharia de payments) consegue navegar do sumário STRIDE aos scores CVSS sem
      precisar consultar nenhum outro documento para entender as afirmações principais

## Merge blockers

O PR não deve ser mergeado enquanto qualquer um dos itens abaixo for falso:

1. `report/threat_model.md` existe e contém todas as seções: STRIDE (4 atores × 3 arquiteturas),
   diagrama da Variante C, 3 cenários compostos, matriz CVSS (21 células), tabela de trade-offs,
   mapeamento de impacto de negócio, tabela de rastreabilidade
2. `report/assets/variante_c_flow.svg` existe e foi gerado com sucesso via `mmdc`
3. Script `scripts/check_threat_model_coverage.py` executa sem erros e reporta 21/21 células cobertas
4. A nota de risco residual qualitativo de model_theft está presente e é consistente com o caveat
   metodológico da Fase 9 (NÃO-APLICÁVEL para reduction_pct)
5. Cada componente do vetor CVSS de cada célula tem justificativa escrita (não apenas o número)
6. A seção "fora do escopo desta fase" está presente e inclui explicitamente: MITRE ATLAS,
   relatório executivo, score Temporal CVSS
7. `specs/tech-stack.md` corrigido: sem ocorrências de "score temporal" referindo-se ao CVSS
8. CI verde (lint + format + type check)
9. Revisão de leitura humana concluída (confirmada pelo autor no PR description)
