# Requirements — Fase 3: RAG e dados para ataques indiretos

## Scope

### In scope

- ChromaDB client singleton e wrapper de embedding (`all-MiniLM-L6-v2`) em `app/infrastructure/rag/`
- Coleção `products`: ingestão idempotente dos 100 produtos do Postgres
- Coleção `faq`: 30 pares pergunta/resposta sintéticos sobre o marketplace
- `POST /api/products` — criação de produto via REST com hook de upsert no Chroma (vetor de RAG poisoning)
- `POST /api/rag/search` — busca semântica sobre as coleções com autenticação
- 5 produtos envenenados no `seed.py` com payloads de prompt injection conhecidos e IDs estáveis
- `scripts/validate_rag.py` — CLI de inspeção de chunks
- Testes pytest cobrindo ingestão idempotente, endpoint de busca e hook de poisoning
- CI instalando `--extra rag` no job de testes

### Out of scope

- Guardrails ou defesas contra RAG poisoning (Fase 9)
- Agente ReAct chamando `search_products` (Fase 4)
- Embedding de mensagens, pedidos ou outros documentos além de produtos e FAQ
- Interface de administração para gerenciar o Chroma
- Logging de queries de busca no `audit_log` (pode ser adicionado na Fase 9)

## Key Decisions

| Decisão | Escolha | Racional |
|---------|---------|----------|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (local) | Roda em CPU, ~80 MB, sem chamada remota, determinístico para os testes |
| ChromaDB versão | `0.5.*` (já fixada em `pyproject.toml`) | Versão já decidida na Fase 1; não alterar |
| ID estável de documento Chroma | `"product_{id}"` / `"faq_{faq_id}"` | Permite `upsert` idempotente sem verificar existência prévia |
| Document text de produto | `"{title}: {description}"` | Concatenação simples favorece recall semântico e mantém payload de poisoning intacto para os ataques |
| Document text FAQ | `"{question}\n{answer}"` | Pergunta e resposta no mesmo chunk reduz fragmentação e melhora relevância |
| Idempotência de ingestão | `collection.upsert()` por ID estável | Re-execução do seed + ingestão não cria duplicatas; sem necessidade de limpar coleção |
| `POST /api/products` sem sanitização | Intencional | Este endpoint é o vetor documentado de RAG poisoning — defesas chegam na Fase 9 |
| IDs dos produtos envenenados | Criados após os 100 normais no seed → IDs 101–105 (com DB limpo) | Estabilidade garantida pela ordem de inserção e pelo `random.seed(42)` já em uso |
| `top_k` padrão no endpoint | 5 para coleção `products`, 3 para `faq` | Balanceia recall vs. ruído no contexto do agente |
| Autenticação no `/api/rag/search` | Qualquer role válido (via `X-API-Key` existente) | Consistente com o padrão das Fases 1–2; sem restrição de role nesta fase |

## Context

### Mission alignment

A Fase 3 constrói a superfície de ataque de **prompt injection indireta** e **RAG poisoning** que serão explorados nas Fases 7 e 8 da matriz 3×6. O `POST /api/products` sem sanitização é uma vulnerabilidade intencional de **insecure plugin design** — um vendedor malicioso pode injetar payloads que o agente vai recuperar e interpretar como instrução. Os produtos envenenados no seed garantem que essa superfície existe desde o início dos testes, com evidências reproduzíveis e IDs conhecidos.

### Tech-stack alignment

- `chromadb==0.5.*` e `sentence-transformers` já declarados em `[project.optional-dependencies] rag` no `pyproject.toml`
- O fix `"extrair rag group"` do CI (2026-05-20) já separou esse grupo; o job de testes precisa de `uv sync --extra rag`
- O fix `"satisfy mypy on redis.get() return type"` (2026-05-20) indica que os novos módulos devem ter anotações de tipo completas para passar no mypy — especialmente o retorno do `collection.query()`, que retorna `QueryResult` com campos opcionais
- `app/infrastructure/rag/` segue o padrão `infrastructure/` da ADR-001: ChromaDB e sentence-transformers ficam confinados aqui; domínio não importa Chroma diretamente

### Dependencies

- **Fase 1**: `docker-compose.yml` já orquestra o container `chroma` com `CHROMA_URL` disponível
- **Fase 2**: `scripts/seed.py` já cria os 100 produtos no Postgres com `random.seed(42)` — os produtos envenenados (IDs 101–105) são adicionados ao final do mesmo script, mantendo o determinismo
- **Fase 2**: `POST /api/products` estende o router existente em `app/infrastructure/web/routers/products.py`
- **Fase 4**: o agente vai chamar `search_products`, que internamente chama `POST /api/rag/search` — a Fase 3 precisa estar completa e os dados ingeridos antes de testar o agente

## Impacto dos fixes do CI (2026-05-20)

Os seguintes fixes afetam diretamente o desenvolvimento da Fase 3:

- **`fix: corrigir CI — optional-dependencies, extrair rag group`**: o grupo `rag` já está em `[project.optional-dependencies]`. O novo job de CI para os testes de RAG deve usar `uv sync --extra rag --group dev` para instalar tanto as dependências de teste quanto as de RAG.
- **`fix: satisfy mypy on redis.get()`**: padrão a seguir — anotar explicitamente retornos de métodos de clientes externos que retornam tipos `Optional`. Em `chromadb`, `collection.query()` retorna `QueryResult`; extrair campos com `or []` ou asserção explícita de tipo.
- **`fix: tool.uv package=false`**: não usar `pip install -e .` no CI. Toda instalação via `uv sync`.
