# Plan — Fase 1: Setup do repositório e ambiente

## 1. Git e estrutura de pastas

- [ ] `git init` no diretório raiz do projeto
- [ ] Criar `.gitignore` cobrindo: `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `evidence/`, `chroma_data/`, `*.db`, `notebooks/.ipynb_checkpoints/`
- [ ] Criar estrutura de pastas completa:
  ```
  app/
    domain/
      ports/          ← arquivos de porta vazios (AgentRuntime, DefenseLayer, EvidenceStore)
      entities/
    application/
      use_cases/
    infrastructure/
      agents/
      defenses/
      persistence/
      web/
  red_team/
    techniques/
    whitebox/
  defenses/
  evidence/
    baseline/
    post_defense/
    whitebox/
  notebooks/
  report/
  scripts/
  tests/
  ```
- [ ] Criar `app/__init__.py` e `__init__.py` em cada subpacote relevante

## 2. Dependências e ambiente Python

- [ ] Criar `pyproject.toml` com `[project]` para Python 3.11, `[project.dependencies]` (fastapi, uvicorn, sqlalchemy, alembic, pydantic, anthropic, openai, groq, langgraph, chromadb, sentence-transformers, redis, pytest, ruff, black, mypy) e `[project.optional-dependencies]` com grupo `whitebox` (torch, transformers)
- [ ] Criar `uv.lock` rodando `uv sync` para fixar versões
- [ ] Validar que `uv sync --no-group whitebox` funciona sem instalar torch

## 3. Docker Compose e infraestrutura

- [ ] Criar `docker-compose.yml` com serviços: `api` (FastAPI), `db` (PostgreSQL 16), `redis` (Redis 7), `chroma` (ChromaDB 0.5), `presidio` (Presidio Analyzer 2.2)
- [ ] Configurar volumes nomeados para `db` e `chroma` com paths fora do OneDrive sync ou dentro de `.gitignore`
- [ ] Criar `Dockerfile` para o serviço `api` baseado em `python:3.11-slim`, copiando código e rodando `uv sync`
- [ ] Testar `docker compose up` e verificar que todos os containers sobem sem erro

## 4. FastAPI app skeleton

- [ ] Criar `app/infrastructure/web/fastapi_app.py` com app FastAPI e rota `GET /health` retornando `{"status": "ok"}`
- [ ] Criar `app/main.py` como entry point (importa e expõe o app)
- [ ] Verificar `curl http://localhost:8000/health` retorna 200 com os containers rodando

## 5. Variáveis de ambiente

- [ ] Criar `.env.example` com: `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `CHROMA_URL`
- [ ] Criar `.env` local (não versionado) com chaves reais para smoke test
- [ ] Adicionar carregamento de `.env` no app via `python-dotenv`

## 6. Portas de domínio (ADR-001)

- [ ] Criar `app/domain/ports/agent_runtime.py` com `Protocol` vazio `AgentRuntime`
- [ ] Criar `app/domain/ports/defense_layer.py` com `Protocol` vazio `DefenseLayer`
- [ ] Criar `app/domain/ports/evidence_store.py` com `Protocol` vazio `EvidenceStore`

## 7. Smoke test de modelos

- [ ] Criar `scripts/smoke_test_models.py` que faz uma chamada mínima a:
  - Claude Sonnet 4.6 via SDK Anthropic (`claude-sonnet-4-6`)
  - Llama 3.1 8B Instant via Groq (`llama-3.1-8b-instant`)
  - Llama Guard 3 via Groq (`llama-guard-3-1b`)
- [ ] Para cada modelo: imprimir latência (ms), tokens usados e primeiros 100 chars da resposta
- [ ] Tratar erros de autenticação com mensagem clara sobre chave ausente no `.env`

## 8. GitHub Actions

- [ ] Criar `.github/workflows/ci.yml` com job único (`quality`) que roda em `push` e `pull_request`:
  - `ruff check .` — lint
  - `black --check .` — format
  - `mypy app/` — type check
- [ ] Configurar `[tool.ruff]`, `[tool.black]` e `[tool.mypy]` no `pyproject.toml`
- [ ] Garantir que o workflow passa localmente antes de fazer push

## 9. README

- [ ] Criar `README.md` com seções: descrição do projeto em 2 parágrafos, pré-requisitos (Docker, Python 3.11, uv), instruções passo a passo (`git clone`, `cp .env.example .env`, editar chaves, `docker compose up`, `python scripts/smoke_test_models.py`), e estrutura de pastas comentada
- [ ] Verificar que o README é suficiente para alguém reproduzir o ambiente a partir de um clone limpo

## 10. Primeiro commit e push

- [ ] `git add` em todos os arquivos (exceto `.env`)
- [ ] Criar commit inicial: `"feat: fase 1 — setup de repositório, ambiente e CI"`
- [ ] Criar repositório no GitHub (nome: `paychat-security-lab` ou equivalente)
- [ ] `git remote add origin` e `git push -u origin main`
