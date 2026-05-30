# Changelog

## 2026-05-29
- feat: Fase 10 — threat model formal (STRIDE + CVSS 21 células + cenários compostos)
- docs(fase-10): adiciona spec da Fase 10 e alinha matriz para 3×7

## 2026-05-27
- feat: Fase 9 — defesas em profundidade: 5 camadas plugáveis (sanitizer NFKC, perplexity GPT-2 anti-GCG, rebuff heurístico + canary, tool_guard com allow-list por perfil e confirmação de refund > R$500, data_classifier) via `DefensePipeline` opt-in (`?defense=on`/`X-Defense`) para Variantes A/B; Variante C mantém pipeline próprio
- feat: `AntiTheftGuard` no rate_limiter — rate limit 60/h por sessão + cooldown por similaridade de queries; rota agent.py retorna 400 (input block) e 429 (anti-theft); `TraceStep` ganha tipo `defense_verdict`
- feat: harness `--defense` (escreve em `evidence/post_defense`, envia `&defense=on`, trata 429 como bloqueio) e `--probing-shared-session` (sessão compartilhada por variante para o anti-theft engajar em model_theft)
- feat: notebook `03_post_defense` — comparação baseline × pós-defesa, redução % por célula com IC Wilson 95%, coluna `block_rate_post` e heatmaps
- fix: heurística pi_direct (lógica recusa-primeiro) — citações do canary/termos do ataque em recusas não contam mais como sucesso; `rescore_pi` re-aplica offline ao baseline (ASR pi_direct A 0.47→0.00, B 0.21→0.14)
- docs: achado metodológico model_theft — anti-theft funciona (bloqueia requisições 61→120 por sessão no limite 60/h), mas ASR e block_rate são indicadores inválidos (controle de volume, não de detecção; ataque vence dentro do threshold) → `reduction_pct` marcado NÃO-APLICÁVEL
- test: suíte unitária das defesas (input, output, plugin, antitheft, disclosure) + heurísticas pi
- chore: Dockerfile rebuild com torch CPU (2.12.0+cpu) + pré-download do GPT-2; pyproject pina torch ao índice CPU; threshold de perplexidade calibrado (1500→8000) para PT benigno

## 2026-05-26
- fix(ci): destrava pipeline — black em 16 arquivos das Fases 6-8 corrige o gate `black --check` que falhava no job quality (primeiro CI verde do histórico)
- chore: hook de pre-commit (black + ruff via `uv run`) espelhando o job quality, evita reincidência de código não formatado
- fix: corrige `type:ignore` com código errado em agent.py (`[union-attr]`→`[attr-defined]`) e supressão consistente em rag.py
- fix: Variante C estágio 3 fail-closed — Presidio indisponível propaga HTTP 503 (sem vazar PII), consistente com o guard
- fix: chromadb 0.5.*→1.5.* corrige KeyError('_type') na busca; ingest_poisoned_products como setup de pi_indirect
- fix: 24 erros de ruff + 17 de mypy em red_team/ (vars de loop, BaseException no gather, type:ignore stubs chromadb)
- test: corrige 4 falhas pré-existentes — isolamento chroma (EphemeralClient compartilhado), desync poison-ID, mock langgraph; + drift guard/provider
- chore: .gitignore exclui evidence/surrogate (modelos GPT-2) e archive; lint limpo em tests/ e agent_trace
- docs: achado pi_indirect — 0% ASR nas 3 variantes (veneno recuperado ~86%, modelos resistem a RAG poisoning)

## 2026-05-25
- feat: Fase 8 — red team completo: matriz 3×7 (variantes A/B/C × 7 categorias) com ≥30 evidências por célula
- feat: catálogos e heurísticas das 4 categorias novas — model_theft, sensitive_disclosure, insecure_plugin (TOCTOU/confused deputy), excessive_agency (multi-turno)
- feat: coleta do baseline Fase 7 (pi_direct, pi_indirect, ioh) para completar a matriz
- feat: surrogate GPT-2 por variante (agreement A=0.90, B=0.73, C=0.65) + apêndice white-box (GCG, MIA)
- feat: notebook 02_baseline_complete — heatmap 3×7, summary.csv e ASR com IC Wilson 95%
- fix: chromadb 0.5.*→1.5.* — corrige KeyError('_type') na busca (mismatch client/server) que invalidava pi_indirect
- chore: concorrência/rate de harness e coletor configuráveis por env (defaults baixos para hosts com pouca RAM)

## 2026-05-21
- feat: Fase 6 — Variante C: pipeline multi-model (Llama Guard + Llama 3.1 8B + Presidio)
- fix: polish Fase 5 — model name, retry delays, BadRequestError handling and parity tests
- feat: Fase 5 — Variante B: agente Llama 3.1 8B via Groq API (OpenAI-compatible)

## 2026-05-20
- feat: Fase 4 — Variante A: agente ReAct Claude (LangGraph + Anthropic)
- docs: spec fase 4 — agente Claude via Anthropic API (LangGraph + 5 tools + trace)
- feat: fase 3 — RAG operacional com ChromaDB, FAQ e superfície de RAG poisoning
- fix: satisfy mypy on redis.get() return type in dependencies
- style: apply black formatting to 5 files
- fix: suprimir E402/I001 no seed.py com ruff noqa de arquivo
- fix: corrigir ordem de imports no seed.py (I001)
- fix: corrigir erros de lint (ruff) no CI
- fix: tool.uv package=false — evita build editable do hatchling no CI
- fix: corrigir CI — optional-dependencies, extrair rag group, remover uv.lock
- fix: migrate dev/whitebox to [dependency-groups] for uv sync --group compatibility

## 2026-05-19
- feat: fase 2 — marketplace base com schema, seed, endpoints REST e audit log
- feat: fase 1 — setup de repositório, ambiente e CI
