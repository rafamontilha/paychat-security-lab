# Requirements — Fase 6: Variante C — Pipeline Multi-Model

## Scope

### In scope

- Estágio 1: Llama Guard 3 via Groq como pré-filtro de input — detecta categorias unsafe e rejeita com 400
- Estágio 2: Llama 3.1 8B via Groq executando o loop ReAct (reutilização por composição do `GroqAgentRuntime` da Variante B)
- Estágio 3: Presidio Analyzer como filtro de output — detecta e redacta PII brasileira e entidades customizadas
- Política de severidade em código (`policy.py`): entidade → ação (`redact` | `block`)
- Recognizers customizados: `PAYMENT_TOKEN` (regex Luhn) e `INTERNAL_SECRET` (prefixos do seed)
- Log estruturado de 4 campos por request persistido em `evidence/`
- Fail-closed em falha de Guard ou Presidio (HTTP 503, sem pass-through)
- Endpoint `POST /api/agent/chat?variant=c` (e header `X-Variant: c`)
- Healthcheck com verificação de conectividade ao Presidio
- Suite `tests/test_variant_c_pipeline.py` com os 3 caminhos obrigatórios
- Não-regressão das Variantes A e B

### Out of scope

- Presidio como filtro de input (apenas output)
- Llama Guard como pós-filtro de output (apenas pré-filtro de input)
- Modificação do `GroqAgentRuntime` — composição sem alteração
- Output perturbation (Post-MVP, depende de acesso a logits)
- Rebuff nesta fase (Fase 9)
- Rate limiting específico da Variante C (Fase 9)
- Uso de Llama Guard como `DefenseLayer` reutilizável nas Variantes A e B (Fase 9 — mas a implementação deve ser desenhada para facilitar isso)

## Key Decisions

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| Modelo do estágio 1 | `llama-guard-3-1b` via Groq | Disponível no catálogo Groq, mesma autenticação da Variante B, latência baixa (1B params), padrão de fato em pipelines defensivos |
| Cliente do estágio 1 | SDK OpenAI-compatible (`openai`) com `base_url` Groq | Mesma abstração da Variante B; consistência no projeto |
| Estágio 2 | Composição de `GroqAgentRuntime` sem duplicação | Garante paridade comportamental com Variante B; qualquer correção em B propaga automaticamente para C |
| Presidio | Container local via HTTP (`http://presidio:5002`) | Já no `docker-compose.yml` desde a Fase 1; soberania de dados (PII não sai do ambiente local) |
| Política de severidade | Tabela estática em `policy.py` | Auditável, testável, sem magic strings em if/else; requisito explícito do merge blocker |
| Fail-closed | `GuardUnavailableError` e `PresidioUnavailableError` → 503 | Segurança by default: pipeline degradado bloqueia em vez de expor |
| TraceStep | Campos novos opcionais (`guard_verdict`, `presidio_findings`) | Preserva compatibilidade para trás com harness da Fase 7 que consome as 3 variantes |
| Log estruturado | Persistido em `evidence/` com timestamp + session_token | Contrato de evidência idêntico às fases anteriores; harness da Fase 7 consome diretamente |

## Context

### Mission alignment

A Variante C é o núcleo do **Entregável 3** do projeto (*Multi-Model Security Architecture Analysis*): demonstrar empiricamente como superfícies de vulnerabilidade compostas emergem quando modelos são orquestrados em pipeline. Sem a Variante C funcionando, a matriz 3×6 fica incompleta e a análise arquitetural comparativa (A vs B vs C) não tem base.

### Tech-stack alignment

- **LangGraph**: `MultiModelPipeline` implementa a porta `AgentRuntime` do ADR-001 como adaptador composto; o grafo LangGraph fica confinado dentro do `GroqAgentRuntime` herdado, não é replicado
- **Presidio 2.2**: container já declarado no `docker-compose.yml`; recognizers customizados usam a API `EntityRecognizer` do Presidio
- **Llama Guard 3** (`llama-guard-3-1b`): versão fixada em `specs/tech-stack.md`
- **Clean Architecture (ADR-001)**: `llama_guard_client.py`, `presidio_client.py` e `pipeline.py` ficam em `app/infrastructure/agents/variant_c/`; `policy.py` é constante de domínio que pode ficar em `app/domain/` ou junto ao adaptador (decisão de implementação a documentar se for para domínio)

### Dependencies

- **Fase 4** — `AgentRuntime` Protocol, `TraceStep` schema (7 campos), `actor_context` por closure, `AgentResponse` contract
- **Fase 5** — `GroqAgentRuntime` implementado e testado; padrão de retry com backoff; tratamento de `BadRequestError`; `test_variant_parity.py` como baseline de paridade
- **Fase 1** — container Presidio Analyzer já no `docker-compose.yml`; variáveis `GROQ_API_KEY` no `.env.example`
- **Fase 2** — seed com dados PII sintéticos (CPF Faker pt_BR, tokens de pagamento) disponíveis para testes de redação
