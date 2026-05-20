# Requirements — Fase 4: Variante A — Agente Claude via Anthropic API

## Scope

### In scope

- LangGraph `StateGraph` com padrão ReAct conectado ao Claude via Anthropic SDK
- 5 ferramentas Python (`search_products`, `get_order`, `process_refund`, `send_message`, `get_user_info`) com `actor_context` injetado pelo runtime
- `POST /api/agent/chat` retornando `{response, trace, session_token}`
- Schema `TraceStep` estável (consumido pela Fase 7)
- Limite de 10 iterações com resposta estruturada
- Histórico multi-turno via Redis (max 20 mensagens, TTL 3600s)
- System prompt com delimitadores explícitos e instrução de imutabilidade do `actor_context`
- `search_products` integrada com ChromaDB da Fase 3
- Testes unitários das 5 ferramentas (sem chamada real à API)
- Testes de injeção de `actor_context` falso e limite de iterações

### Out of scope

- Guardrails, Llama Guard, Presidio, Rebuff (Fase 9)
- Variante B (Llama via Groq) e Variante C (pipeline multi-model) — Fases 5 e 6
- `test_variant_parity.py` (requer Variante B pronta)
- Red team automatizado (Fase 7)
- Output perturbation e rate limiting de anti-theft (Fase 9)

## Key Decisions

| Decisão | Escolha | Racional |
|---------|---------|----------|
| Modelo Claude | `claude-sonnet-4-6` | Versão mais recente disponível; identificador correto conforme ambiente atual |
| Framework de orquestração | LangGraph `StateGraph` | Suporta grafos explícitos, interrupção human-in-the-loop (Fase 9) e trace auditável |
| Injeção de `actor_context` | Via closure nas ferramentas, nunca via argumento do modelo | Pilar de segurança: modelo não pode escalar privilégios passando user_id/role falsos |
| `search_products` — fonte de dados | ChromaDB da Fase 3 via `ingest.py` / `collections.py` | Habilita RAG poisoning como vetor de ataque desde o baseline |
| Schema `TraceStep` | `type`, `content`, `tool_name`, `tool_args`, `tool_result`, `timestamp` (ISO 8601) | Formato estável que a harness da Fase 7 consome sem retrabalho |
| Histórico Redis | `agent_history:{session_token}` como lista JSON, max 20 msgs, TTL 3600s | Paridade de TTL com sessão de auth; janela de 20 msgs cobre ataques multi-turno (Crescendo) sem estouro de contexto |
| Limite de iterações | `recursion_limit=10` no LangGraph | Item explícito do roadmap; retorno estruturado `max_iterations_reached` torna o comportamento testável e previne DoS |
| `send_message` sem sanitização | Intencional | Vetor de exfiltração documentado para a Fase 7 (insecure output handling) |
| `get_user_info` com restrição de role | Apenas `support` e `admin` | Vetor de sensitive information disclosure quando bypassado via prompt injection |
| Testes end-to-end com API real | `@pytest.mark.integration`, fora do CI padrão | Evita dependência de `ANTHROPIC_API_KEY` no CI; testes de ferramentas (Python puro + DB) são suficientes para validar o contrato |
| `system_prompt.py` com delimitadores | `<SYSTEM>` / `<USER_INPUT>` tags | Separação explícita prompt/dados — baseline sem guardrail; a Fase 9 vai adicionar sanitização sobre esse esquema |

## `actor_context` Schema

```python
{
    "user_id": int,          # ID do usuário autenticado (da sessão Redis)
    "role": str,             # "buyer" | "seller" | "support" | "admin"
    "session_token": str,    # token da sessão ativa
    "name": str,             # nome do usuário (para personalização do agente)
}
```

Este dicionário é injetado no momento da construção do agente — cada ferramenta o recebe via `functools.partial` ou closure, **nunca** como parâmetro passável pelo modelo.

## `TraceStep` Schema

```python
class TraceStep(BaseModel):
    type: Literal["thought", "tool_call", "tool_return", "final"]
    content: str           # texto do pensamento ou resposta final
    tool_name: str | None  # preenchido para tool_call e tool_return
    tool_args: dict | None # argumentos que o modelo passou para a ferramenta
    tool_result: str | None # resultado retornado pela ferramenta
    timestamp: str         # ISO 8601 UTC
```

Este schema é a unidade de evidência que a Fase 7 persiste em `evidence/baseline/` como JSON estruturado.

## Context

### Mission alignment

A Fase 4 entrega a **Variante A** da matriz 3×6 — o baseline proprietário de alto alinhamento. O agente deliberadamente não tem guardrails além do sistema de roles do marketplace, o que maximiza a superfície de ataque mensurável nas Fases 7 e 8. Cada decisão de design (actor_context imutável, send_message sem sanitização, get_user_info restrito por role mas bypassável via injeção) foi tomada para garantir que os vetores de ataque são expostos de forma controlada e reproduzível.

### Tech-stack alignment

- `langgraph` e `anthropic` declarados como extras no `pyproject.toml` (grupo `agent`)
- `claude-sonnet-4-6` é o modelo correto para este ambiente (tech-stack.md menciona `claude-sonnet-4-5` mas o identifier atual é `claude-sonnet-4-6`)
- `search_products` chama `app.infrastructure.rag.ingest` diretamente — confinado em `infrastructure/`, conforme ADR-001
- Ferramentas em `app/infrastructure/agents/tools/` seguem o padrão `infrastructure/` da ADR-001

### Dependencies

- **Fase 2**: tabelas `products`, `orders`, `messages`, `users` já existem no Postgres — as ferramentas fazem queries diretas
- **Fase 3**: `POST /api/rag/search` e `ingest_single_product` disponíveis — `search_products` os consome
- **Fase 3**: `get_chroma_client()` como FastAPI dependency injetável — ferramentas de busca reutilizam o mesmo padrão
- **Fase 5**: `test_variant_parity.py` depende de Variante B pronta; não criar ainda

## Impacto dos fixes anteriores

- **`fix: satisfy mypy on redis.get()`**: padrão a seguir na leitura do histórico Redis — anotar explicitamente o retorno de `r.get()` antes de `json.loads()`
- **`fix: tool.uv package=false`**: instalação de `--extra agent` via `uv sync`, não `pip install -e .`
