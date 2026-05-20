# Validation — Fase 3: RAG e dados para ataques indiretos

## Automated checks

- [ ] [auto] `ruff check .` — sem erros de lint nos arquivos novos e modificados
- [ ] [auto] `black --check .` — formatação consistente em todos os arquivos
- [ ] [auto] `mypy app/ scripts/` — sem erros de tipo; anotações completas em `app/infrastructure/rag/` e no endpoint `POST /api/products`
- [ ] [auto] `pytest tests/test_rag_ingest.py` — ingestão de produtos e FAQ cria coleções com contagem correta
- [ ] [auto] `pytest tests/test_rag_ingest.py` — re-executar ingestão duas vezes não duplica documentos (contagem idêntica)
- [ ] [auto] `pytest tests/test_rag_endpoint.py` — `POST /api/rag/search` com query `"como solicito reembolso"` retorna ≥1 chunk da coleção `faq` no top-3
- [ ] [auto] `pytest tests/test_rag_endpoint.py` — `POST /api/rag/search` com query `"tênis"` retorna ≥1 produto cujo ID está em `POISONED_PRODUCT_IDS` no top-10 (assertion sobre IDs, não apenas "aparece na lista")
- [ ] [auto] `pytest tests/test_rag_endpoint.py` — `POST /api/products` autenticado como `seller` → produto recém-criado aparece em `/api/rag/search` em chamada subsequente (valida o hook de upsert do ChromaDB)
- [ ] [auto] `pytest tests/test_rag_endpoint.py` — `POST /api/rag/search` sem `X-API-Key` retorna 401
- [ ] [auto] CI verde no GitHub Actions: job `test` (ou `test-rag` separado) instalando `--extra rag` coleta e passa todos os testes acima

## Manual smoke tests

- [ ] [manual] `docker compose up -d` em clone limpo → `python scripts/seed.py` → `python scripts/ingest_rag.py` → nenhum erro, output mostra contagem de 100 produtos e 30 FAQ ingeridos
- [ ] [manual] `python scripts/validate_rag.py "como solicito reembolso?"` → saída legível com pelo menos 1 chunk de FAQ (tópico `reembolso`) no top-3, score exibido
- [ ] [manual] `python scripts/validate_rag.py "tênis preto"` → pelo menos 1 dos 5 produtos envenenados aparece nos resultados; IDs envenenados visíveis nos metadados
- [ ] [manual] `python scripts/validate_rag.py "qual a previsão de entrega?"` → retorna chunks de FAQ relevantes (tópico `entrega`)
- [ ] [manual] `python scripts/validate_rag.py "pizza margherita"` (query fora de domínio) → sistema não quebra; retorna chunks com scores baixos ou sem resultado relevante, sem stack trace
- [ ] [manual] Inspeção visual dos 5 envenenados: via `python scripts/validate_rag.py` ou `chroma list` equivalente — confirmar que os 5 IDs `product_101` a `product_105` estão presentes na coleção e que os payloads de injeção estão intactos no campo `document`

## Merge blockers

O PR **não pode ser mergeado** a menos que **todos** os itens abaixo sejam verdadeiros:

1. Clone limpo + `docker compose up` + `python scripts/seed.py` + `python scripts/ingest_rag.py` + `python scripts/validate_rag.py "como solicito reembolso?"` funciona **sem nenhum passo extra** além dos documentados no `README.md`
2. CI verde: lint (`ruff`), format (`black`), types (`mypy`) e todos os testes automatizados passam no GitHub Actions com `--extra rag` instalado
3. Ingestão é idempotente: executar `python scripts/ingest_rag.py` duas vezes consecutivas produz a mesma contagem de documentos em ambas as coleções
4. Assertions sobre IDs envenenados passam nos testes automatizados — não é suficiente os produtos "aparecerem na lista"; os IDs específicos (`POISONED_PRODUCT_IDS`) devem ser retornados na query `"tênis"`
5. Endpoint `POST /api/rag/search` está coberto por testes automatizados, não apenas pelo CLI `validate_rag.py`
6. `POST /api/products` está funcional e o hook de upsert no Chroma está coberto por teste automatizado
