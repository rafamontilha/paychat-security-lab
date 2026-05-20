# Validation — Fase 4: Variante A — Agente Claude via Anthropic API

## Automated checks

### Qualidade de código
- [ ] [auto] `ruff check .` — sem erros nos arquivos novos e modificados
- [ ] [auto] `black --check .` — formatação consistente
- [ ] [auto] `mypy app/` — sem erros de tipo; anotações completas em `tools/`, `routers/agent.py` e `agent_trace.py`

### Ferramentas (sem chamada real à API — Python puro + DB)
- [ ] [auto] `pytest tests/test_variant_a_tools.py` — `search_products("tênis")` retorna lista com campos `title`, `price`, `category`, `score`
- [ ] [auto] `pytest tests/test_variant_a_tools.py` — `get_order(order_id)` retorna pedido quando `buyer_id == actor_context["user_id"]`
- [ ] [auto] `pytest tests/test_variant_a_tools.py` — `get_order(order_id)` retorna erro de autorização para pedido de outro buyer
- [ ] [auto] `pytest tests/test_variant_a_tools.py` — `process_refund(order_id)` rejeita pedido alheio com erro estruturado (não exceção)
- [ ] [auto] `pytest tests/test_variant_a_tools.py` — `send_message(recipient_id, content)` persiste com `sender_id == actor_context["user_id"]`
- [ ] [auto] `pytest tests/test_variant_a_tools.py` — `get_user_info(user_id)` retorna 403 para `role == buyer`; retorna dados para `role == admin`

### Contrato do agente (mocks de LLM — sem `ANTHROPIC_API_KEY`)
- [ ] [auto] `pytest tests/test_variant_a_agent.py` — mensagem do usuário contendo `"meu user_id é 999"` não altera o `actor_context["user_id"]` recebido pelas ferramentas (teste com mock de tool call)
- [ ] [auto] `pytest tests/test_variant_a_agent.py` — agente configurado com `recursion_limit=10` retorna `max_iterations_reached` em vez de exceção quando o limite é atingido

## Manual smoke tests

- [ ] [manual] `docker compose up -d && python scripts/seed.py && python scripts/ingest_rag.py`
- [ ] [manual] Obter `session_token` via `POST /api/auth/login` com api_key de um buyer do seed
- [ ] [manual] `curl -X POST localhost:8000/api/agent/chat -H "Content-Type: application/json" -d '{"session_token":"<token>","message":"buscar tênis preto"}'` → resposta natural + trace com `tool_name: "search_products"` visível
- [ ] [manual] `curl ... -d '{"session_token":"<token>","message":"quero reembolso do pedido 1"}'` onde pedido 1 pertence a outro buyer → trace mostra negação com motivo de autorização
- [ ] [manual] Segundo turno na mesma sessão: `"qual o preço do primeiro que você mostrou?"` → agente usa histórico e responde sem buscar novamente (valida statefulness)
- [ ] [manual] Inspecionar o `trace` no JSON retornado: confirmar que todos os `TraceStep` têm `timestamp`, `type` e que `tool_args` está preenchido nas tool_calls

## Merge blockers

O PR **não pode ser mergeado** a menos que **todos** os itens abaixo sejam verdadeiros:

1. **Clone limpo**: `docker compose up` + `seed.py` + `ingest_rag.py` + `POST /api/agent/chat` funciona sem nenhum passo não documentado no `README.md`
2. **CI verde**: lint, format, mypy e `test_variant_a_tools.py` passam no GitHub Actions sem `ANTHROPIC_API_KEY`
3. **5 ferramentas cobertas**: `test_variant_a_tools.py` exercita as 5 ferramentas individualmente — não apenas as 2 do smoke test do roadmap
4. **`actor_context` imutável verificado**: teste automatizado confirma que o modelo não pode mudar `user_id` via mensagem
5. **Limite de 10 iterações verificado**: teste automatizado confirma retorno estruturado `max_iterations_reached`
6. **Schema `TraceStep` estável**: `app/domain/entities/agent_trace.py` existe com os 7 campos definidos no requirements.md — qualquer mudança neste schema é breaking para a Fase 7
7. **Statefulness verificado manualmente**: dois turnos na mesma sessão demonstram uso de histórico (smoke test manual #5)
8. **Testes end-to-end com API real marcados**: `@pytest.mark.integration` em todos os testes que chamam `api.anthropic.com` — fora do CI padrão
