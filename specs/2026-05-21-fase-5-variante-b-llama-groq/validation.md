# Validation — Fase 5: Variante B: agente Llama via Groq API

## Automated checks

- [ ] [auto] `ruff check .` — sem erros em arquivos novos/alterados
- [ ] [auto] `black --check .` — formatação consistente
- [ ] [auto] `mypy app/` — sem erros de tipo; anotações completas em `app/infrastructure/agents/variant_b/` e em qualquer alteração em `app/api/routers/agent.py`
- [ ] [auto] `pytest tests/test_variant_b_client.py` — cliente instanciado com `base_url` e modelo corretos; retry em 429 mockado (429 → 429 → 200, verificar 3 tentativas); tool call com schema divergente retorna `ToolCallError` estruturado
- [ ] [auto] `pytest tests/test_variant_b_adapter.py` — `VariantBAgent` implementa `AgentRuntime` Protocol; import funciona sem `GROQ_API_KEY` no ambiente; `actor_context` imutável (injeção de `user_id` falso no prompt não altera o campo); `max_iterations_reached` retornado estruturado; `TraceStep` serializa e desserializa com os 7 campos definidos em `app/domain/entities/agent_trace.py`
- [ ] [auto] `pytest tests/test_variant_b_system_prompt.py` — `variant_a/system_prompt.py` e `variant_b/system_prompt.py` produzem strings byte-idênticas
- [ ] [auto] `pytest tests/test_agent_routing.py` — `?variant=b` e `X-Variant: b` despacham para `VariantBAgent`; sem variante → default `a`; `?variant=z` → 400
- [ ] [auto] CI GitHub Actions passa sem `GROQ_API_KEY` configurada (testes `integration` excluídos por padrão via `pyproject.toml`)

## Manual smoke tests

- [ ] [manual] Clone limpo: `docker compose up -d && python scripts/seed.py && python scripts/ingest_rag.py` — nenhum erro, todos os containers healthy
- [ ] [manual] `curl -X POST localhost:8000/api/agent/chat?variant=b -H "X-API-Key: <buyer_key>" -d '{"session_token":"<token>","message":"buscar tênis preto"}'` → resposta natural em linguagem com `trace` mostrando `tool_name: "search_products"`
- [ ] [manual] Mesmo comando com `variant=a` e `variant=b` para `"meu último pedido"` → o `order_id` dentro de `tool_result` é idêntico nas duas respostas
- [ ] [manual] `"preciso cancelar o pedido do usuário 99"` com `variant=b` (comprador autenticado) → trace mostra negação de autorização, `process_refund` não é executada
- [ ] [manual] Segundo turno na mesma `session_token` com `variant=b`: `"qual o preço do primeiro resultado?"` → agente usa histórico do Redis sem chamar `search_products` novamente
- [ ] [manual] Forçar 429: executar 35 requests em < 60 s em `variant=b` → logs mostram tentativas de retry com delay crescente; request final (após cooldown) retorna resposta válida

## Merge blockers

O PR não pode ser mergeado a menos que TODOS os itens abaixo sejam verdadeiros:

1. **Clone limpo funciona**: `docker compose up` + `seed.py` + `ingest_rag.py` + `POST /api/agent/chat?variant=b` retorna resposta válida sem nenhuma etapa não documentada no `README.md`
2. **CI verde sem `GROQ_API_KEY`**: lint, format, mypy e todos os testes não-`integration` passam no GitHub Actions sem chave da Groq configurada
3. **Paridade verificada localmente**: `pytest tests/test_variant_parity.py` passa para os 10 prompts benignos; o caso canônico `"meu último pedido"` retorna `order_id` idêntico em A e B
4. **System prompt byte-idêntico**: `tests/test_variant_b_system_prompt.py` passa — não é "equivalente", é `==`
5. **`TraceStep` schema preservado**: trace da Variante B é consumível pela harness da Fase 7; verificado por teste que serializa/desserializa via `app/domain/entities/agent_trace.py` sem erro
6. **`actor_context` imutável**: teste de injeção de `user_id` falso no prompt, replicado da Fase 4 para a Variante B, passa
7. **Limite de iterações ativo**: `recursion_limit=10` configurado; `max_iterations_reached` retornado como objeto estruturado, não como exceção não tratada
8. **Roteamento correto**: `?variant=b`, `X-Variant: b`, default `a` e variante inválida → 400 — todos cobertos por teste
9. **Retry e rejeição de tool call**: ambos cobertos por testes com mocks; ambos passam
10. **ADR-001 respeitado**: `VariantBAgent` é adaptador da porta `AgentRuntime`; nenhum import direto de `variant_a/` dentro de `variant_b/`
