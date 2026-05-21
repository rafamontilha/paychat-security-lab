# Plan — Fase 5: Variante B: agente Llama via Groq API

## 1. Groq client

- [ ] Adicionar dependência `openai>=1.55` ao `pyproject.toml` (já fixada no tech-stack; confirmar que está presente)
- [ ] Confirmar identifier corrente do modelo na console Groq e fixar `GROQ_MODEL=llama-3.1-8b-instant` no `.env.example`
- [ ] Criar `app/infrastructure/agents/variant_b/groq_client.py` — instancia `openai.AsyncOpenAI` com `base_url=https://api.groq.com/openai/v1` e `api_key=GROQ_API_KEY`
- [ ] Implementar retry com backoff exponencial em 429 (máx 3 tentativas, delays 1s, 2s, 4s)
- [ ] Implementar rejeição estruturada de tool calls com schema divergente: validar via Pydantic, retornar `ToolCallError` ao agente sem derrubar a request
- [ ] Escrever `tests/test_variant_b_client.py` cobrindo: instanciação, retry em 429 (mock), rejeição de tool call malformada (mock)

## 2. Adaptador da porta AgentRuntime (Variante B)

- [ ] Criar `app/infrastructure/agents/variant_b/__init__.py` e `build_agent()` que segue o mesmo contrato de `variant_a/`
- [ ] Adaptar o loop ReAct LangGraph para usar o cliente Groq (trocar apenas o LLM backend; ferramentas, `actor_context` e `recursion_limit` herdados sem alteração)
- [ ] Garantir que tool call malformada do Llama conta como uma iteração no `recursion_limit=10`
- [ ] Garantir que `actor_context` é injetado por closure, nunca exposto como argumento ao modelo
- [ ] Garantir que o histórico Redis usa a chave `agent_history:{session_token}` com max 20 mensagens e TTL 3600 s (mesma estrutura da Variante A)
- [ ] Escrever `tests/test_variant_b_adapter.py`: Protocol compliance, import sem `GROQ_API_KEY`, `actor_context` imutável, `max_iterations_reached`, `TraceStep` com os 7 campos corretos

## 3. System prompt e endpoint

- [ ] Criar `app/agents/variant_b/system_prompt.py` produzindo string byte-idêntica ao `variant_a/system_prompt.py`
- [ ] Escrever `tests/test_variant_b_system_prompt.py` com assert de igualdade byte-a-byte entre os dois arquivos
- [ ] Adicionar seleção de variante em `POST /api/agent/chat`: query `?variant=b` e header `X-Variant: b`; default `a`; retornar 400 para variante inválida
- [ ] Escrever `tests/test_agent_routing.py`: `?variant=b`, `X-Variant: b`, default `a`, variante inválida

## 4. Suite de paridade

- [ ] Criar `tests/test_variant_parity.py` com `@pytest.mark.integration` e 10 prompts benignos cobrindo as 5 ferramentas (2 redações por ferramenta)
- [ ] Definir os 10 prompts no arquivo como constante `PARITY_PROMPTS` (lista documentada no arquivo)
- [ ] Asserção: `first_tool_call(trace_a) == first_tool_call(trace_b)` para cada prompt
- [ ] Smoke test canônico do roadmap: "meu último pedido" → `order_id` idêntico em A e B

## 5. CI e documentação

- [ ] Garantir que `tests/test_variant_parity.py` fica fora do job de CI padrão (marcador `integration` excluído por padrão no `pyproject.toml` `[tool.pytest.ini_options]`)
- [ ] Atualizar `README.md` da fase com instrução para smoke tests manuais e paridade local
- [ ] Atualizar `CHANGELOG.md` com entrada da Fase 5
