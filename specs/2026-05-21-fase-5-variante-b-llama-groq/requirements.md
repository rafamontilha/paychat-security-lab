# Requirements — Fase 5: Variante B: agente Llama via Groq API

## Scope

### In scope

- Cliente Groq via SDK OpenAI-compatible (`openai.AsyncOpenAI` com `base_url=https://api.groq.com/openai/v1`)
- Modelo `llama-3.1-8b-instant` fixado em `.env.example` como `GROQ_MODEL`
- Adaptador `VariantBAgent` implementando a porta `AgentRuntime` (ADR-001)
- Loop ReAct LangGraph idêntico ao da Variante A, com troca apenas do LLM backend
- As mesmas 5 ferramentas da Variante A: `search_products`, `get_order`, `process_refund`, `send_message`, `get_user_info`
- `actor_context` injetado por closure no runtime, nunca exposto como argumento ao modelo
- System prompt byte-idêntico ao de `variant_a/system_prompt.py`
- `recursion_limit=10` por turno; tool call malformada conta como uma iteração
- Conversação stateful via Redis: chave `agent_history:{session_token}`, max 20 mensagens, TTL 3600 s
- `TraceStep` com os 7 campos definidos na Fase 4 (schema preservado para a harness da Fase 7)
- Roteamento em `POST /api/agent/chat`: `?variant=b` ou `X-Variant: b`; default `a`; 400 para variante inválida
- Retry com backoff exponencial em 429 do Groq (máx 3 tentativas: 1 s, 2 s, 4 s)
- Rejeição estruturada de tool calls com schema divergente: `ToolCallError` retornado ao agente, loop continua
- Suite `tests/test_variant_parity.py` com 10 prompts benignos e marcador `@pytest.mark.integration`

### Out of scope

- Guardrails de qualquer tipo (Llama Guard, Presidio, Rebuff, sanitização de input, perplexity filter) — Fase 9
- Pipeline multi-model (Llama Guard → Llama → Presidio) — Fase 6 (Variante C)
- Harness de red team, payloads, evidence store — Fase 7
- Rate limiting de anti-theft e output perturbation — Fase 9 (o retry em 429 é tolerância a falha do provedor, não defesa)
- Qualquer mudança no system prompt em relação à Variante A (diferenças observadas nas Fases 7–8 devem ser atribuídas ao modelo, não ao prompt)
- Upgrade para Llama 3.3 70B — post-MVP explícito no tech-stack
- Ataques white-box contra Llama 3.1 8B via Groq (Groq não expõe logits/gradientes) — apêndice white-box em GPT-2, Fase 8

## Key Decisions

| Decisão | Escolha | Rationale |
|---------|---------|-----------|
| SDK de acesso ao Groq | `openai.AsyncOpenAI` com `base_url` ajustada | API OpenAI-compatible permite uma única abstração para A e B na harness; sem dependência adicional além do `openai` já fixado |
| LLM backend na harness de A e B | LangGraph com adapter de cliente, mesmo grafo | Paridade comportamental garantida por construção (ADR-001); diferenças no trace vêm do modelo, não da orquestração |
| Comportamento de tool call malformada | `ToolCallError` retornado ao agente; conta como 1 iteração no limite de 10 | Evita loop infinito em modelo menos alinhado; mantém o trace auditável para a Fase 7 |
| Compartilhamento de código com Variante A | Via `app/domain/` e `app/application/` apenas; `variant_a/` e `variant_b/` são adaptadores independentes | ADR-001: nenhum acoplamento direto entre adaptadores |
| System prompt | Arquivo `variant_b/system_prompt.py` produz string byte-idêntica ao de `variant_a/` | Garantia testável de que diferenças na matriz 3×6 são atribuíveis ao modelo |
| Testes de integração (paridade) | `@pytest.mark.integration`; excluídos do CI padrão via `pyproject.toml` | CI não precisa de `GROQ_API_KEY`; paridade é verificada localmente antes do merge |

## Context

### Mission alignment

A Fase 5 entrega a Variante B — o segundo ponto de dado da matriz 3×6. Sem ela, não há comparativo que responda "qual arquitetura LLM resiste melhor a cada classe de ataque?" para a dimensão open-source vs. proprietário. A suíte de paridade é o que garante que as diferenças observadas nas Fases 7–8 são atribuíveis ao modelo, não à orquestração.

### Tech-stack alignment

- Modelo: `llama-3.1-8b-instant` via Groq (free tier, 14.400 req/dia, API OpenAI-compatible — tech-stack §3)
- Orquestração: LangGraph (tech-stack §2), mesmo grafo da Variante A com troca de LLM backend
- Persistência de sessão: Redis 7 (tech-stack §4), mesma estrutura de chave e TTL da Fase 4
- Arquitetura: ADR-001 — `VariantBAgent` como adaptador da porta `AgentRuntime`

### Dependencies

- **Fase 4** — define o contrato herdado: `AgentRuntime` Protocol, `TraceStep` schema, `actor_context` por closure, Redis key pattern, `recursion_limit=10`, ferramentas e seus schemas
- **Fase 3** — RAG operacional: `search_products` depende do ChromaDB e dos embeddings ingeridos
- **Fase 2** — schema PostgreSQL: `get_order`, `process_refund`, `send_message`, `get_user_info` dependem das tabelas e seed
