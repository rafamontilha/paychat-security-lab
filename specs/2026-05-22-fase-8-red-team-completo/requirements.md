# Requirements — Fase 8: Red Team Completo

## Scope

### In scope

- Implementação dos catálogos de payloads e heurísticas de avaliação para as 4 categorias restantes:
  `model_theft`, `sensitive_disclosure`, `insecure_plugin`, `excessive_agency`
- Extensão da harness existente (`red_team/harness.py`) e do modelo de dados (`EvidenceRecord`)
  para suportar as novas categorias — sem criar novo pipeline
- Coleta de 500 pares query/response por variante e fine-tuning de GPT-2 surrogate (Bloco 1b)
- Execução da matriz completa 3 variantes × 4 categorias com ≥ 30 evidências por célula
- Apêndice white-box: GCG e MIA contra GPT-2 small, evidências em `evidence/whitebox/`
- Notebook `02_baseline_complete.ipynb` preenchido com matriz 3×6 + heatmap + CSV exportado
- Payloads multi-turno para logic-chain injection (extensão mínima de `AttackPayload`)

### Out of scope

- Implementação de qualquer defesa (Fase 9)
- Re-execução das 3 categorias da Fase 7 (PI direta, PI indireta, IOH) — evidências da Fase 7
  são consumidas pelo notebook sem re-execução
- Ataques white-box contra os modelos de produção (Claude, Llama via Groq) — sem acesso a logits
- Surrogate model training com modelo maior que GPT-2 small
- Cálculo de CVSS ou impacto de negócio (Fase 10)

---

## Key Decisions

| Decisão | Escolha | Rationale |
|---------|---------|-----------|
| Reutilizar harness da Fase 7 | Estender `harness.py` e `EvidenceRecord` | Paridade de schema; evidências das 6 categorias ficam em `evidence/baseline/` com estrutura uniforme |
| Fronteira model_theft vs sensitive_disclosure | `model_theft`: mede completude da extração; `sensitive_disclosure`: mede tipo de conteúdo vazado | Mesmo payload pode gerar duas evidências com `success_flag` distintos — critério operacional é o `success_flag` primário |
| Target de evidências: insecure_plugin | 30 por variante com cobertura das 3 técnicas (TOCTOU + parâmetros + confused deputy) | Número de técnicas é limitado; distribuição interna desigual é aceitável se todas as 3 forem cobertas |
| TOCTOU em ambiente single-worker | Se race impraticável: código de demonstração com mock da janela | Prioridade é documentar a vulnerabilidade conceitual; a harness não garante paralelismo real em servidor FastAPI single-worker |
| Payloads multi-turno | `AttackPayload` estendido com `turns: list[str]` (opcional) | Retrocompatibilidade garantida: default `[payload]` mantém Fase 7 funcionando sem alteração |
| White-box isolado | `evidence/whitebox/` separado de `evidence/baseline/` | White-box é apêndice do relatório; não entra no cálculo de ASR comparativo entre variantes |
| Surrogate training: GPT-2 small | GPT-2 small como surrogate de Claude, Llama A, B e C | Demonstra o pipeline end-to-end; GPT-2 cabe na RTX 3050 4GB; não há claim de precisão — o valor é mostrar o ataque funcionando |
| Success flag excessive_agency | Ação privilegiada executada com sucesso (efeito colateral produzido) | Diferente de PI (Fase 7) que mede obediência; aqui o critério é o *efeito* da ação, não a técnica utilizada |

---

## Context

### Mission alignment

A Fase 8 completa o **Entregável 1 — LLM Vulnerability Assessment** da especialização Applied AI Engineering:
todas as 6 categorias de vulnerabilidade exigidas estarão cobertas com técnicas de ataque documentadas
e análise de causa raiz. Sem a Fase 8, a matriz 3×6 central do projeto permanece incompleta,
inviabilizando a comparação quantitativa entre arquiteturas que é o núcleo do relatório executivo.

O apêndice white-box atende ao requisito de "both API-based and embedded model architectures"
do enunciado, demonstrando ataques que são possíveis quando pesos estão acessíveis (GPT-2 small)
mas impossíveis nas variantes de produção (Claude, Llama via Groq).

### Tech-stack alignment

- **Harness**: extensão direta de `red_team/harness.py`; adere a ADR-001 (harness consome porta
  `AgentRuntime`, nunca adaptadores diretamente)
- **Evidências**: schema `EvidenceRecord` uniforme para todas as 6 categorias; `evidence/baseline/`
  consumido pelos notebooks sem re-execução
- **Rate limiting**: pools independentes Anthropic / Groq da Fase 7 são reaproveitados sem alteração;
  coleta de 500 pares para surrogate (Bloco 1b) cabe no free tier de 14.4K req/dia do Groq
- **White-box**: `torch >= 2.5` e `transformers >= 4.46` já listados no `pyproject.toml` como
  dependências opcionais do apêndice; GPT-2 small cabe na RTX 3050 de 4 GB
- **Notebook**: `notebooks/02_baseline_complete.ipynb` já existe como esqueleto; esta fase o preenche

### Dependencies

- **Fase 7 concluída**: evidências em `evidence/baseline/` para PI direta, PI indireta e IOH;
  harness e modelos de dados operacionais
- **Seed data disponível**: 50 usuários, 100 produtos, 200 pedidos do `scripts/seed.py` (Fase 2);
  produtos envenenados do `scripts/seed.py` (Fase 3) — necessários para cenários de excessive agency
  e sensitive disclosure
- **Variantes A, B, C operacionais**: `POST /api/agent/chat?variant={a,b,c}` (Fases 4, 5, 6)
- **ChromaDB populado**: necessário para tool chaining via `search_products` (Fase 3)
