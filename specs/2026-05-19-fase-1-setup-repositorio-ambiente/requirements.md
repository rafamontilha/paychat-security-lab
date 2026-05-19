# Requirements — Fase 1: Setup do repositório e ambiente

## Scope

### In scope

- Inicialização do repositório Git local e criação do repositório no GitHub
- Estrutura de pastas completa conforme ADR-001 (Clean Architecture right-sized)
- `pyproject.toml` com todas as dependências fixadas conforme `tech-stack.md`
- `docker-compose.yml` orquestrando PostgreSQL 16, Redis 7, ChromaDB e Presidio Analyzer
- FastAPI app skeleton com `GET /health` retornando `{"status": "ok"}`
- Arquivo `.env.example` com todas as variáveis de ambiente necessárias
- Script `scripts/smoke_test_models.py` validando Claude Sonnet 4.6, Llama 3.1 8B e Llama Guard 3
- GitHub Actions com lint (`ruff`), format check (`black`) e type check (`mypy`) em cada PR
- `README.md` com instruções completas de setup local

### Out of scope

- Qualquer lógica de negócio (usuários, produtos, pedidos) — Fase 2
- Schema de banco de dados além do container saudável — Fase 2
- Agentes ReAct ou tool calling — Fases 4–6
- Scripts de red team — Fase 7+

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Gerenciador de pacotes | `uv` + `pyproject.toml` | Resolução mais rápida, lock file determinístico; compatível com Python 3.11+ |
| Grupos de dependências no pyproject | `[project.dependencies]` + `[project.optional-dependencies]` separados por camada (app, dev, whitebox) | Permite `uv sync --no-group whitebox` para manter o ambiente leve sem torch/transformers no fluxo principal |
| Modelo Anthropic na smoke test | `claude-sonnet-4-6` | tech-stack.md refere `claude-sonnet-4-5`, mas o modelo corrente da API é `claude-sonnet-4-6` — usar o atual |
| Inicialização git | `git init` na Fase 1 | O working directory ainda não é um repositório Git; a fase cria e faz o primeiro commit |
| Localização do repo | `C:\Users\rafae\OneDrive\Documentos\Projetos\LLM_Sec_And_Vulnerabilities` | Pasta existente com OneDrive sync — arquivos grandes (ChromaDB data, evidence/) devem ir no `.gitignore` para evitar sync desnecessário |
| Scripts cross-platform | Todos os scripts Python rodam dentro de containers Linux via Docker; comandos shell no README usam sintaxe Docker Compose agnóstica de OS | Ambiente de desenvolvimento é Windows 11 + PowerShell; os containers resolvem a diferença de plataforma |
| Estrutura de portas (ADR-001) | Criar arquivos de porta vazios em `app/domain/ports/` desde a Fase 1 | Garante que Fases 4–6 possam plugar variantes sem refatorar estrutura |

## Context

### Mission alignment

A Fase 1 é o pré-requisito técnico para toda a matriz 3×6. Sem ambiente reproduzível e smoke test das três APIs validado, nenhuma fase seguinte pode começar com confiança. A meta Distinction do enunciado exige que a matriz inteira seja reproduzível a partir de um clone limpo — isso começa aqui.

### Tech-stack alignment

Todas as versões fixadas conforme `tech-stack.md`. Atenção especial:
- `langgraph 0.2` — apenas estrutura de pastas na Fase 1; implementação real na Fase 4
- `chromadb 0.5` — container no compose; client Python instalado mas não inicializado
- `presidio-analyzer 2.2` — container no compose; integração real na Fase 6

### Dependencies

Nenhuma fase anterior. Esta é a fase fundacional.

### Environment constraints

- **OS de desenvolvimento:** Windows 11 Home, PowerShell — comandos no README devem mencionar que `docker compose up` é o único comando necessário no host
- **RAM:** 8 GB no host; todos os containers juntos consomem ~1.5 GB com ChromaDB e PostgreSQL idle
- **OneDrive sync:** adicionar `evidence/`, `*.db`, `chroma_data/`, `.venv/` ao `.gitignore` para evitar sync de gigabytes de dados experimentais
