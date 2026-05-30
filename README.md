# PayChat Security Lab

Auditoria sistemática de segurança em três arquiteturas de LLM aplicadas a um marketplace conversacional de payments. Capstone da especialização **Applied AI Engineering** — nível Distinction.

O projeto implementa três variantes funcionalmente equivalentes de um assistente ReAct (Claude Sonnet 4.6, Llama 3.3 70B via Together AI, pipeline multi-model com Llama Guard 4 + Presidio), executa uma matriz de ataques 3×7 contra cada variante e mede a efetividade de defesas em profundidade.

## Pré-requisitos

| Ferramenta | Versão mínima |
|---|---|
| Docker Desktop | 24+ |
| Python | 3.11+ |
| uv | 0.4+ (`pip install uv`) |
| Git | 2.40+ |

Chaves de API necessárias:
- `ANTHROPIC_API_KEY` (Variante A) — [console.anthropic.com](https://console.anthropic.com)
- `LLM_API_KEY` (Variantes B/C, Together AI) — [api.together.xyz](https://api.together.xyz)
- `GROQ_API_KEY` (opcional, provider legado) — [console.groq.com](https://console.groq.com)

## Setup local

```bash
# 1. Clonar o repositório
git clone https://github.com/<seu-usuario>/paychat-security-lab.git
cd paychat-security-lab

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env e preencher ANTHROPIC_API_KEY (Variante A) e LLM_API_KEY (Variantes B/C, Together AI)

# 3. Subir a infraestrutura
docker compose up -d

# 4. Validar que a API está no ar
curl http://localhost:8000/health
# Esperado: {"status":"ok"}

# 5. Instalar dependências Python (para scripts locais)
uv sync

# 6. Validar conectividade com os três modelos
python scripts/smoke_test_models.py
```

## Estrutura do projeto

```
app/
  domain/
    ports/          # Interfaces (AgentRuntime, DefenseLayer, EvidenceStore)
    entities/       # Modelos Pydantic (Attack, Evidence, Finding)
  application/
    use_cases/      # execute_attack, apply_defense, compute_metrics
  infrastructure/
    agents/         # Implementações das Variantes A, B, C
    defenses/       # Llama Guard, Presidio (mock), detector heurístico (Rebuff-style), rate limiter
    persistence/    # filesystem_evidence, postgres_audit
    web/            # FastAPI app, routers, middleware
red_team/
  harness.py        # Orquestrador principal da matriz de ataques
  techniques/       # Ataques por categoria
  whitebox/         # Scripts GCG/MIA contra GPT-2 (apêndice)
evidence/           # Artefatos JSON de cada execução (não versionados)
notebooks/          # Análise e visualização da matriz
report/             # Threat model e relatório executivo
scripts/
  smoke_test_models.py   # Valida as três APIs
  seed.py                # Popula o banco com dados sintéticos (Fase 2)
  validate_rag.py        # Testa o pipeline RAG (Fase 3)
specs/              # Documentação de fases: missão, roadmap, tech-stack
```

## Variantes

| Variante | Modelo | Arquitetura |
|---|---|---|
| A | Claude Sonnet 4.6 (Anthropic API) | API-based proprietário |
| B | Llama 3.3 70B Instruct Turbo (Together AI) | Embedded open-source |
| C | Llama Guard 4 + Llama 3.3 70B + Presidio | Pipeline multi-model |

## Reprodutibilidade

Toda execução de ataque persiste um artefato JSON em `evidence/` com timestamp, payload, response e `success_flag`. Os notebooks consomem esses artefatos — nunca re-executam ao vivo. Para reproduzir a matriz completa a partir de um clone limpo:

```bash
docker compose up -d
python scripts/seed.py        # Fase 2 — popula o banco
python red_team/harness.py    # Fase 7+ — executa a matriz
```

## CI

GitHub Actions roda lint (`ruff`), format check (`black`) e type check (`mypy`) em cada pull request.
