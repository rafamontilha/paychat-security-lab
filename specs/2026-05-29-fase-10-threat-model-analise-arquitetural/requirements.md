# Requirements — Fase 10: Threat Model e Análise Arquitetural

## Scope

### In scope
- `report/threat_model.md`: documento consolidado com STRIDE, diagrama, cenários compostos,
  matriz CVSS, tabela de trade-offs e mapeamento de impacto de negócio
- Diagrama de fluxo da Variante C em Mermaid (fonte embutida no Markdown) + export SVG via `mmdc`
- STRIDE aplicado aos 4 atores (comprador, vendedor, suporte, atacante externo) nas 3 arquiteturas (A, B, C)
- 3 cenários de vulnerabilidade composta no pipeline multi-model:
  - Cenário 1: injeção sobrevive ao Llama Guard, capturada pelo Presidio
  - Cenário 2: Presidio passa, Llama Guard captura
  - Cenário 3: composição cria brecha que nenhuma camada veria isoladamente
- Matriz CVSS v3.1 por (variante, categoria): 21 células com score Base + Environmental;
  justificativa escrita por componente do vetor; coluna de risco residual qualitativo
- Tabela de rastreabilidade: finding da matriz 3×7 → ameaça STRIDE → score CVSS
- Mapeamento de impacto de negócio: account takeover, vendor impersonation, chargeback fraud,
  regulatory non-compliance — alimenta a coluna Environmental da matriz CVSS
- Tabela de trade-offs A/B/C: latência, custo por 1M requests, complexidade operacional
- Correção pontual de `specs/tech-stack.md`: "score temporal" → "score Environmental"

### Out of scope
- Mapeamento para MITRE ATLAS (Post-MVP, conforme roadmap)
- Relatório executivo (`report/SECURITY_AUDIT.md`) — Fase 11
- Novas categorias ou payloads de ataque não coletados nas Fases 7–9
- Ataques em tempo de treinamento (backdoor, data poisoning) — fora do escopo global do projeto
- Score Temporal do CVSS v3.1 (não aplicável: informações de exploitability pública e remediação
  não estão disponíveis para LLM em marketplace sintético)
- Certificação de compliance formal (PCI-DSS, SOC 2) — discutida como recomendação, não entregável

## Key Decisions

| Decisão | Escolha | Rationale |
|---|---|---|
| Ferramenta de diagrama | Mermaid embutido + SVG via mmdc | Texto puro, diffável, renderiza nativo no GitHub; SVG necessário para Pandoc PDF na Fase 11 |
| Nível CVSS | Base + Environmental; Temporal ausente | Environmental contextualiza para payments (CR/IR/AR); Temporal requer dados de exploitability pública indisponíveis |
| Número de cenários compostos | 3 | Cobre as duas direções (Guard↔Presidio) + o caso de falha composta — achado mais valioso para o Entregável 3 |
| Justificativa do vetor CVSS | Uma frase por componente por célula | Auditável por CISO/compliance; evita que scores pareçam arbitrários |
| Risco residual model_theft | Nota qualitativa explícita, não score numérico | reduction_pct = NÃO-APLICÁVEL na Fase 9; inflar Environmental score seria inconsistente com o caveat metodológico registrado |
| MITRE ATLAS | Fora de escopo | Post-MVP no roadmap; reabrir nesta fase forçaria escopo e não há coleta de dados adicional |
| Tabela de rastreabilidade | Incluída como sub-tarefa explícita | Torna o critério "done when" mecânico: revisão via tabela, não leitura linha a linha |

## Context

### Mission alignment
A Fase 10 entrega o Entregável 3 do enunciado: "Multi-Model Security Architecture Analysis".
O threat model formal com STRIDE e a análise de vulnerabilidades compostas do pipeline
multi-model são o que separa o nível Distinction do Proficient no critério de avaliação.
A tabela de trade-offs A/B/C responde diretamente à pergunta do relatório executivo:
"qual arquitetura LLM resiste melhor a cada classe de ataque?"

### Tech-stack alignment
- Diagrama em Mermaid alinha com a decisão de Markdown + Pandoc (camada de entrega) e com o
  requisito de reprodutibilidade: o fonte é texto puro no repo. O export SVG via `mmdc`
  (Mermaid CLI) é pré-requisito para o `make report-pdf` da Fase 11.
- A matriz CVSS consome evidências de `evidence/baseline/` e `evidence/post_defense/`
  (coletadas nas Fases 7–9). Nenhum dado novo é gerado; a Fase 10 é análise pura.
- O caveat metodológico de model_theft (NÃO-APLICÁVEL) vem do `CHANGELOG` e do notebook 03;
  o threat model deve ser consistente com essa documentação.

### Dependencies
- Fase 9 completa: matriz pós-defesa coletada (1902 registros, 0 erros), notebook 03 rodado,
  headline pi_direct variante B = -93%, caveat model_theft sem --probing-shared-session registrado
- `evidence/post_defense/` disponível como fonte de dados para o scoring CVSS Environmental
- Nenhuma chamada de API ou execução de ataque necessária nesta fase (análise pura)
