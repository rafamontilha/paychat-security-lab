# Validation — Fase 2: Marketplace base

## Automated checks

- [ ] [auto] `ruff check .` passa sem erros
- [ ] [auto] `black --check .` passa sem erros
- [ ] [auto] `mypy app/` passa sem erros de tipo
- [ ] [auto] `alembic upgrade head` conclui sem erro em ambiente limpo (executa no CI via `docker compose run api`)
- [ ] [auto] `pytest tests/test_marketplace_smoke.py` — suite que valida programaticamente:
  - `POST /api/auth/login` com API key válida retorna 200 com `session_token` e `role`
  - `GET /api/products` retorna lista não-vazia
  - `GET /api/orders` retorna pedidos do comprador autenticado
  - `POST /api/messages` com session de comprador retorna 201
  - `GET /api/users/{id}` com session de comprador retorna 403
  - `POST /api/refunds` com pedido de outro usuário retorna 403
  - Após cada chamada, `audit_log` possui entrada correspondente (verificado via query direta ao banco)

## Manual smoke tests

- [ ] [manual] `docker compose up` inicia todos os containers sem erro
- [ ] [manual] `python scripts/seed.py` conclui sem erro e imprime contagens: 50 usuários, 100 produtos, 200 pedidos, 50 transações
- [ ] [manual] Sequência completa de `curl` (ou `Invoke-WebRequest`) no PowerShell:
  1. `POST /api/auth/login` com API key de um comprador → salvar `session_token`
  2. `GET /api/products` com session token → lista de produtos retornada
  3. `GET /api/orders` com session token → pedidos do comprador retornados
  4. `GET /api/orders/{id}` com pedido de outro usuário → 403
  5. `POST /api/messages` com `recipient_id` de um vendedor → 201
  6. `POST /api/refunds` com pedido próprio → 200 ou 202
  7. `POST /api/refunds` com pedido de outro usuário → 403
- [ ] [manual] Query direta em `audit_log` confirma entradas para cada chamada da sequência acima
- [ ] [manual] `python scripts/seed.py` pode ser reexecutado sem duplicar dados ou lançar erro de constraint

## Merge blockers

A Fase 2 não pode ser considerada concluída a menos que TODOS os itens abaixo sejam verdadeiros:

1. `alembic upgrade head` recria o schema completo a partir de zero sem intervenção manual
2. `python scripts/seed.py` popula a base com dados corretos em um ambiente limpo (clone fresco + `docker compose up`)
3. Sequência manual de `curl` (autenticar → listar produtos → abrir pedido → enviar mensagem) funciona e aparece registrada em `audit_log`
4. RBAC: `GET /api/users/{id}` retorna 403 para perfil `buyer`; `POST /api/refunds` retorna 403 para pedido de outro usuário
5. `pytest tests/test_marketplace_smoke.py` passa no CI sem necessidade de setup adicional além de `docker compose up`
6. GitHub Actions CI (`quality` + novo job `test`) aparece verde no push do PR
