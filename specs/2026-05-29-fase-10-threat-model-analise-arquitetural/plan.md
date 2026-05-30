# Plan — Fase 10: Threat Model e Análise Arquitetural

## 1. Bloco 1 — Fundação estrutural: diagrama da Variante C + STRIDE

O diagrama de fluxo deve preceder o STRIDE da arquitetura C porque nomeia os estágios
(Llama Guard → ReAct → Presidio) onde a propagação composta acontece. STRIDE dos 4 atores
pode correr em paralelo com o diagrama, pois os atores independem do fluxo interno.

- [ ] Criar `report/threat_model.md` com estrutura de seções completa (esqueleto vazio)
- [ ] Desenhar diagrama de fluxo da Variante C em Mermaid: identificar os 3 estágios,
      entradas/saídas de cada um e pontos de propagação de ataques entre estágios
- [ ] Exportar diagrama para SVG via `mmdc` e salvar em `report/assets/variante_c_flow.svg`
      (necessário para o `make report-pdf` da Fase 11 — Mermaid não renderiza no Pandoc sem esse passo)
- [ ] Aplicar STRIDE aos 4 atores (comprador, vendedor, suporte, atacante externo) nas 3 arquiteturas:
      preencher tabela STRIDE no threat_model.md
- [ ] Validar cobertura: cada célula da matriz 3×7 baseline tem pelo menos uma ameaça STRIDE
      correspondente

## 2. Bloco 2 — Cenários compostos e scoring CVSS

Os 3 cenários compostos precisam anteceder o CVSS porque definem o caminho de ataque
específico que determina os componentes do vetor (especialmente Scope e métricas de impacto).

- [ ] Documentar Cenário 1: injeção sobrevive ao Llama Guard mas é capturada pelo Presidio
      — descrever payload, estágio de bypass, estágio de captura, impacto residual
- [ ] Documentar Cenário 2: Presidio passa, Llama Guard pega — descrever os mesmos campos
- [ ] Documentar Cenário 3: ambas as camadas falham ou a composição cria a brecha
      — este é o achado arquitetural mais valioso para o Entregável 3; documentar por que
      a composição introduz a vulnerabilidade que nenhuma das camadas veria isoladamente
- [ ] Montar matriz CVSS v3.1 por (variante, categoria): 21 células
      — scores Base e Environmental (CR/IR/AR ajustados para payments)
      — Temporal explicitamente ausente (documentar decisão na seção de escopo)
- [ ] Escrever justificativa por escrito de cada componente do vetor CVSS para cada célula
      (uma frase por componente AV/AC/PR/UI/S/C/I/A + CR/IR/AR contextualizado para payments)
- [ ] Adicionar coluna "Risco residual qualitativo" na matriz: nota narrativa onde o CVSS
      não captura a realidade medida pela Fase 9
      — em especial: model_theft (reduction_pct = NÃO-APLICÁVEL; risco residual não coberto
        pelo Environmental score) e cenários compostos onde a composição cria a brecha
- [ ] Mapear cada finding para impacto de negócio: account takeover, vendor impersonation,
      chargeback fraud, regulatory non-compliance — esta coluna alimenta o Environmental score

## 3. Bloco 3 — Tabela de trade-offs e rastreabilidade

- [ ] Construir tabela de trade-offs A/B/C: latência média (ms, medida nas execuções anteriores),
      custo operacional estimado por 1M requests, complexidade de operação (qualitativa)
- [ ] Construir tabela de rastreabilidade finding → ameaça STRIDE → score CVSS
      — uma linha por célula da matriz 3×7 (21 linhas)
      — torna a revisão final do "done when" mecânica, não manual

## 4. Higiene de escopo e consistência

- [ ] Corrigir `specs/tech-stack.md`: substituir toda ocorrência de "score temporal" / "Temporal"
      referente ao CVSS por "score Environmental" (o projeto usa Base + Environmental, não Temporal)
- [ ] Seção "fora do escopo desta fase" explícita no threat_model.md:
      MITRE ATLAS, relatório executivo (Fase 11), novas categorias/payloads de ataque,
      ataques em tempo de treinamento
- [ ] Revisão de leitura humana: leitura completa do threat_model.md garantindo que cada
      afirmação tem evidência referenciada e sem ambiguidade para leitor externo
