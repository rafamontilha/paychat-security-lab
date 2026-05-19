# Validation — Fase 1: Setup do repositório e ambiente

## Automated checks

- [ ] [auto] `ruff check .` passa sem erros
- [ ] [auto] `black --check .` passa sem erros
- [ ] [auto] `mypy app/` passa sem erros de tipo
- [ ] [auto] GitHub Actions CI job (`quality`) aparece verde no commit de push inicial
- [ ] [auto] `uv sync --no-group whitebox` conclui sem erro e não instala `torch` nem `transformers`

## Manual smoke tests

- [ ] [manual] `docker compose up` inicia todos os 5 containers (`api`, `db`, `redis`, `chroma`, `presidio`) sem erros no log
- [ ] [manual] `curl http://localhost:8000/health` (ou `Invoke-WebRequest` no PowerShell) retorna HTTP 200 com body `{"status":"ok"}`
- [ ] [manual] `python scripts/smoke_test_models.py` (com `.env` preenchido) imprime latência e resposta válida para os três modelos: Claude Sonnet 4.6, Llama 3.1 8B e Llama Guard 3
- [ ] [manual] Clonar o repositório em uma pasta nova, copiar `.env.example` para `.env`, preencher as chaves — `docker compose up` funciona sem nenhum passo adicional
- [ ] [manual] Verificar que `.env` não aparece em `git status` (protegido pelo `.gitignore`)
- [ ] [manual] Verificar que os arquivos de porta `app/domain/ports/agent_runtime.py`, `defense_layer.py`, `evidence_store.py` existem com `Protocol` definido

## Merge blockers

A Fase 1 não pode ser considerada concluída a menos que TODOS os itens abaixo sejam verdadeiros:

1. `docker compose up` inicia todos os containers sem erro em ambiente limpo (clone fresco)
2. `curl localhost:8000/health` retorna 200
3. `python scripts/smoke_test_models.py` imprime resposta válida dos três modelos
4. GitHub Actions CI passa no repositório remoto
5. `.env` não está versionado
6. `README.md` contém instruções suficientes para reproduzir o ambiente sem assistência adicional
