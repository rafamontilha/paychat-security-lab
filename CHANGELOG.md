# Changelog

## 2026-05-20
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
