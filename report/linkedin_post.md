# Draft — Post LinkedIn (Fase 12)

> Rascunho para revisão. Nada aqui é publicado automaticamente — a publicação é manual (ver checklist no fim).

---

## Imagem

**Primária (recomendada):** `report/figures/heatmap_baseline.png` — heatmap da matriz 3×7 (3 arquiteturas × 7 vetores), ASR baseline por célula. É a figura que comunica o eixo central do projeto numa imagem.

**Alternativa (conta a história antes/depois):** `report/figures/matrix_baseline_post_reduction.png` — baseline vs pós-defesa com a redução por célula.

> Sugestão de legenda da imagem: *"Matriz 3×7: attack success rate por arquitetura (A/B/C) × vetor de ataque."*

---

## Título

**LLM Security: Vulnerabilities and Defense Patterns — Applied AI Engineering Specialization**

---

## Copy (~200 palavras · PT)

Acabei de concluir o **PayChat Security Lab** — uma auditoria de segurança aplicada a LLMs em payments, capstone da especialização *Applied AI Engineering*.

A pergunta de partida: qual arquitetura de agente conversacional resiste melhor a ataques? Para responder com rigor, construí **três variantes funcionalmente equivalentes** de um marketplace com agente ReAct — Claude Sonnet 4.6 (API proprietária), Llama 3.3 70B via Together AI (open-source gerenciado) e um **pipeline multi-model** (Llama Guard 4 → Llama 70B → Presidio) — e ataquei cada uma contra **7 vetores do OWASP LLM Top 10**, gerando uma matriz de evidências **3×7** medida antes e depois de defesas em profundidade.

Alguns achados:
→ Onde a defesa atua sobre **conteúdo**, a redução é real: prompt injection direta caiu **93%** no Llama, e o Llama Guard 4 barrou **92%** das injeções já na entrada.
→ **Excessive agency** via injeção atingiu **CVSS 9.1 (Critical)** — escalada de papel que, em payments, é chargeback fraud.
→ Contra **model theft**, a "redução" é **NÃO-APLICÁVEL**: rate limiting é controle de volume, não de conteúdo. Expor a quebra do indicador foi mais honesto que inflar um número.

Relatório executivo, threat model STRIDE e código reproduzível no repositório. 👇

🔗 https://github.com/rafamontilha/paychat-security-lab

#LLMSecurity #AIEngineering #ApplicationSecurity #Payments #OWASP #RedTeam #AppliedAI

---

## Entrada "Projetos" do perfil (campo curto)

**Nome:** PayChat Security Lab — LLM Security: Vulnerabilities and Defense Patterns

**Descrição (≤ 2 linhas):**
Auditoria de segurança de 3 arquiteturas LLM (API-based, open-source gerenciado, pipeline multi-model) para marketplace de payments: matriz 3×7 de ataques baseline vs defesas em profundidade, threat model STRIDE + CVSS e relatório executivo reproduzível. Stack: Claude Sonnet 4.6, Llama 3.3 70B (Together AI), Llama Guard 4, LangGraph, FastAPI.

**URL:** https://github.com/rafamontilha/paychat-security-lab

---

## Checklist de publicação (handoff manual — você executa)

- [ ] Revisar a copy e ajustar tom/idioma (versão EN disponível sob pedido)
- [ ] Anexar a imagem do heatmap (`report/figures/heatmap_baseline.png`)
- [ ] Confirmar que o link do repo abre sem login (repo público)
- [ ] Publicar o post
- [ ] Adicionar a entrada em "Projetos" no perfil
