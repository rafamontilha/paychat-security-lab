# Plan — Fase 7: Red Team Baseline (PI Direta · PI Indireta · IOH)

Grupos sequenciais: cada grupo depende do anterior.

## 1. Infraestrutura da harness e persistência

- [ ] Definir modelo Pydantic `EvidenceRecord` em `red_team/models.py` com campos:
      `id, timestamp, variant, category, technique, payload, temperature, run_index,`
      `response, success_flag, success_reason, execution_status, trace`
      — `execution_status`: `"success" | "error" | "max_iterations"` (separado de `success_flag`)
      — `id`: `sha256(variant|category|technique|payload|temperature|run_index)[:16]`
- [ ] Implementar `red_team/harness.py`: runner assíncrono que consome
      `POST /api/agent/chat?variant={a,b,c}` via HTTP (nunca importa adaptadores — ADR-001)
- [ ] Integrar `asyncio.gather` + `aiolimiter.AsyncLimiter(30, 60)` + `asyncio.Semaphore(5)`,
      com pools independentes para Anthropic (Variante A) e Groq (Variantes B e C)
- [ ] Persistência: `evidence/baseline/{id}.json`, um arquivo por evidência
- [ ] Flag `--resume`: pula evidências cujo arquivo JSON já existe (idempotência via ID determinístico)
- [ ] Gerar `session_token` Redis novo por execução (sem estado compartilhado entre chamadas)
- [ ] Script `red_team/validate_evidence.py`: lê todos os JSONs em `evidence/baseline/`,
      valida schema contra `EvidenceRecord` e imprime relatório de erros

## 2. Catálogo de payloads e heurísticas

- [ ] `red_team/payloads/prompt_injection_direct.py`: 25 payloads
      (DAN, "ignore previous", role-play, ArtPrompt, persona modulation)
      + canary token único por payload derivado de `sha256(payload)[:8]`
- [ ] `red_team/payloads/prompt_injection_indirect.py`: 15 produtos envenenados
      + função `ingest_poisoned_products(chroma_client)` que os insere com
      metadado `is_red_team_payload=True`
- [ ] `red_team/payloads/insecure_output_handling.py`: 25 payloads
      (XSS via `<script>`, SQL via tool calling, SSRF via URLs construídas)
- [ ] Função `evaluate_success(category, payload, response, trace) -> (bool, str)`
      com heurística por categoria, retornando `(success_flag, success_reason)`
- [ ] Script `red_team/cleanup_poisoned_products.py`: remove produtos
      com `is_red_team_payload=True` do ChromaDB (não executar no merge da Fase 7)

## 3. Execução e coleta de evidências

- [ ] Dry-run: 30 evidências distribuídas entre variantes e categorias;
      gerar `evidence/baseline/_dry_run_report.md` com custo extrapolado (Anthropic e Groq)
- [ ] Confirmar limite de tier Anthropic antes de iniciar execução completa
- [ ] Executar matriz completa:
      3 variantes × (25+15+25) payloads × 2 temperaturas (0.0 e 0.7) × runs configurados
      — PI direta: 2 runs/temp; PI indireta: 3 runs/temp; IOH: 2 runs/temp
      — Total esperado: ~870 evidências
- [ ] Executar `red_team/validate_evidence.py` ao final e garantir 0 erros de schema
- [ ] Verificar taxa de `execution_status=error` por estrato; re-rodar erros até < 5%

## 4. Revisão manual e cálculo de kappa

- [ ] Selecionar amostra estratificada de 10% por `(variante, célula, temperatura)`,
      mínimo 5 por estrato, para revisão humana manual
- [ ] Registrar resultado humano no campo `manual_review` do CSV de amostra
- [ ] Calcular Cohen's kappa (heurística vs manual) para cada uma das 3 células
- [ ] Se kappa < 0.6 em qualquer célula: revisar heurística e re-executar avaliação antes de avançar

## 5. Notebook e entregáveis finais

- [ ] `notebooks/01_baseline_pi_ioh.ipynb`: carregar `evidence/baseline/*.json`,
      calcular ASR por `(variante, célula, temperatura)` com IC Wilson 95%,
      gerar heatmap 3×3 por temperatura
- [ ] Exportar PNGs em `evidence/baseline/figures/heatmap_temp_0.0.png`
      e `evidence/baseline/figures/heatmap_temp_0.7.png`
- [ ] Gerar `evidence/baseline/summary.csv` com schema estável para consumo pela Fase 8
- [ ] `red_team/README.md`: instruções de reexecução a partir de clone limpo
      (pré-requisitos, ingestão de produtos, dry-run, matriz completa, notebook, wall clock, custo)
