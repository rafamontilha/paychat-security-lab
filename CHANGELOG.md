# Changelog

## 2026-05-26
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
