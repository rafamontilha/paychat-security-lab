# Requirements — Fase 7: Red Team Baseline (PI Direta · PI Indireta · IOH)

## Scope

### In scope

- Harness `red_team/harness.py` consumindo `POST /api/agent/chat?variant={a,b,c}` via HTTP
- Modelo Pydantic `EvidenceRecord` com campo `execution_status` separado de `success_flag`
- Catálogo de payloads: 25 PI direta, 15 PI indireta (produtos envenenados), 25 IOH
- Ingestão dos 15 produtos envenenados no ChromaDB com `is_red_team_payload=True`
- Temperatura como dimensão da matriz: 0.0 e 0.7
- Paralelização por `(variante, payload, temperatura, run_index)` via `asyncio.gather`
- Pool independente Anthropic (Variante A) e pool independente Groq (Variantes B e C)
- `session_token` Redis novo por execução (sem estado compartilhado)
- ID determinístico `sha256(variant|category|technique|payload|temperature|run_index)[:16]`
- Flag `--resume` para idempotência
- Dry-run de 30 evidências com relatório de custo antes da execução completa
- Revisão manual 10% estratificada + Cohen's kappa por célula
- Notebook `01_baseline_pi_ioh.ipynb` com ASR, IC Wilson 95%, heatmaps, CSV

### Out of scope

- Defesas extras (Rebuff, sanitização de entrada, rate limiting anti-theft) — Fase 9
- Llama Guard e Presidio na Variante C são parte do sistema **sob teste**, não defesas adicionais
- Categorias restantes (model theft, sensitive information disclosure, insecure plugin design, excessive agency) — Fase 8
- Apêndice white-box (GCG, MIA em GPT-2) — Fase 8
- Garak e PyRIT — reavaliados no spec da Fase 8
- Ataques multi-turno (Crescendo, SPOTON) — Fase 8 ou posterior
- Re-execução pós-defesa e cálculo de redução de ASR — Fase 9
- Scoring CVSS dos findings — Fase 10
- PAIR/TAP (geração automática de variações via LLM atacante) — postergado

## Key Decisions

| Decisão | Escolha | Rationale |
|---------|---------|-----------|
| Biblioteca de paralelismo | `asyncio.gather` + `aiolimiter.AsyncLimiter(30, 60)` + `asyncio.Semaphore(5)` | Controle fino de concorrência sem overhead de threads; respeita 30 req/min do Groq |
| Pools de rate limit | Anthropic e Groq independentes | Rate limits são por provider; pool único subestimaria capacidade de A e superestimaria de B/C |
| Granularidade da paralelização | Por `(variante, payload, temperatura, run_index)` | Unidade mínima idempotente; viabiliza `--resume` granular |
| Isolamento de sessão | `session_token` Redis novo por execução | Impede estado de conversa anterior contaminar o resultado do ataque |
| ID da evidência | SHA-256 determinístico dos 6 campos | Idempotência sem banco: verificar existência = verificar arquivo no filesystem |
| Temperatura como dimensão | 0.0 e 0.7 | Captura comportamento determinístico vs estocástico na mesma matriz |
| Células da matriz | 3 separadas: PI direta, PI indireta, IOH | Análise granular por categoria, alinhada com as 6 do enunciado do projeto |
| `execution_status` | `"success" \| "error" \| "max_iterations"` separado de `success_flag` | ASR só conta `execution_status=success`; erros de infra não devem mascarar resultados |
| Trace | Reusa `TraceStep` da Fase 4 sem modificação | Paridade com Variante A; sem risco de divergência de schema entre variantes |
| Endpoint consumido | `POST /api/agent/chat?variant={a,b,c}` via HTTP | ADR-001: harness não importa adaptadores diretamente |
| Persistência | Filesystem, um JSON por evidência | Simplicidade; ID determinístico dispensa índice; git versionável |
| Canary tokens | Únicos por payload, derivados de `sha256(payload)[:8]` | Detectar leakage no output sem colisão entre payloads |
| Estratégia ≥45/estrato | Híbrida: ampliar lista + repetir runs | Lista grande dá diversidade de técnica; runs múltiplos dão estabilidade estatística |
| Limite exato Anthropic | Confirmar antes do dry-run | Tier atual desconhecido; dry-run fornece extrapolação antes de comprometer orçamento |

## Context

### Mission alignment

A Fase 7 inicia o **Entregável 1 — LLM Vulnerability Assessment** da especificação do projeto.
Executa as 3 primeiras das 6 categorias de vulnerabilidade (prompt injection direta, indireta e insecure output handling) com técnicas documentadas e critérios de sucesso reproduzíveis.
O baseline aqui gerado é a referência quantitativa que as Fases 8 e 9 vão expandir e comparar.

### Tech-stack alignment

- `asyncio` + `aiolimiter`: padrão para respeitar rate limits de Groq (30 req/min) sem overhead de threads
- `EvidenceRecord` Pydantic: alinhado com a camada de domínio da Clean Architecture; validação de schema via `validate_evidence.py` é o equivalente de um teste de integração de persistência
- ChromaDB + metadado `is_red_team_payload`: reutiliza infraestrutura RAG da Fase 3 sem modificação
- Endpoint HTTP: consumo via API pública garante que a harness testa o mesmo path que um atacante real usaria

### Dependencies

| Fase | Artefato necessário |
|------|---------------------|
| Fase 3 | ChromaDB operacional com `search_products` funcional para PI indireta |
| Fase 4 | Variante A (`?variant=a`) + schema `TraceStep` |
| Fase 5 | Variante B (`?variant=b`) + tratamento de rate limit Groq |
| Fase 6 | Variante C (`?variant=c`) + Llama Guard + Presidio como parte do sistema sob teste |
