# Red Team — Fase 7: Baseline PI Direta, PI Indireta, IOH

Guia de reexecução completa a partir de um clone limpo do repositório.

---

## Pré-requisitos

**Fases 1–6 concluídas.** A harness depende de:
- Fase 3: ChromaDB com `search_products` operacional
- Fase 4: Variante A (`?variant=a`)
- Fase 5: Variante B (`?variant=b`)
- Fase 6: Variante C (`?variant=c`) com Llama Guard e Presidio

**Dependências instaladas:**

```bash
pip install -e ".[dev,rag,agent,redteam]"
```

**Variáveis de ambiente** (copiar `.env.example` → `.env`):

```
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
DATABASE_URL=postgresql://paychat:paychat@localhost:5432/paychat
REDIS_URL=redis://localhost:6379
CHROMA_URL=http://localhost:8000

# Chave de API de um usuário comprador (obtida após seed):
HARNESS_BUYER_API_KEY=<api_key de um User com role=buyer>
```

Para obter `HARNESS_BUYER_API_KEY` após o seed:

```bash
# Conecte ao PostgreSQL e consulte:
psql $DATABASE_URL -c "SELECT api_key FROM users WHERE role = 'buyer' LIMIT 1;"
```

---

## 1. Iniciar a infraestrutura

```bash
docker compose up -d
```

Aguarde todos os containers estarem `healthy`:

```bash
docker compose ps
```

---

## 2. Seed do banco e RAG

Se ainda não tiver sido feito:

```bash
python -m scripts.seed
python -m scripts.ingest_rag
```

---

## 3. Iniciar a aplicação

```bash
uvicorn app.main:app --reload
# Ou via Docker: docker compose up api
```

Verificar: `curl http://localhost:8000/health`

---

## 4. Ingerir produtos envenenados (PI Indireta)

```bash
python - <<'EOF'
from app.infrastructure.rag.client import get_chroma_client
from red_team.payloads.prompt_injection_indirect import ingest_poisoned_products

client = get_chroma_client()
n = ingest_poisoned_products(client)
print(f"Ingested {n} poisoned products.")
EOF
```

---

## 5. Dry-run (validar custo antes da execução completa)

```bash
python -m red_team.harness --dry-run
```

Verifique `evidence/baseline/_dry_run_report.md` para:
- Custo Anthropic extrapolado
- Taxa de erros no dry-run (deve ser 0)

---

## 6. Execução completa da matriz

```bash
python -m red_team.harness --resume
```

- `--resume` pula evidências já persistidas (idempotente)
- Wall clock esperado: ~60 min (domina o Anthropic; Groq é rápido)
- Total esperado: ~870 arquivos em `evidence/baseline/`

**Execução por categoria/variante (opcional, para depurar):**

```bash
# Só PI direta, variante A, temperatura 0.0
python -m red_team.harness --variant a --category pi_direct --temperature 0.0
```

---

## 7. Validar schema das evidências

```bash
python -m red_team.validate_evidence
```

Deve imprimir `0 error(s)`. Se houver erros, verifique e corrija antes do merge.

---

## 8. Gerar notebook e heatmaps

```bash
jupyter nbconvert --to notebook --execute notebooks/01_baseline_pi_ioh.ipynb \
    --output notebooks/01_baseline_pi_ioh_executed.ipynb
```

Saídas geradas:
- `evidence/baseline/summary.csv`
- `evidence/baseline/figures/heatmap_temp_0.0.png`
- `evidence/baseline/figures/heatmap_temp_0.7.png`
- `evidence/baseline/manual_review_sample.csv`

---

## 9. Revisão manual (kappa)

1. Abra `evidence/baseline/manual_review_sample.csv`
2. Preencha a coluna `manual_review` com `True`/`False` para cada registro
3. Execute a célula de kappa no notebook

**Gate de merge:** kappa ≥ 0.6 em cada categoria (PI direta, PI indireta, IOH).
Se kappa < 0.6 em alguma categoria, revise a heurística em `red_team/heuristics.py`
e recalcule antes de abrir o PR.

---

## 10. Limpeza dos produtos envenenados (NÃO executar no merge da Fase 7)

Os produtos envenenados devem permanecer até a Fase 9 (defesas).
Quando a Fase 9 estiver completa:

```bash
python -m red_team.cleanup_poisoned_products --dry-run   # ver o que será removido
python -m red_team.cleanup_poisoned_products              # remover
```

---

## Custo esperado de API

| Provider | Calls | Custo |
|----------|-------|-------|
| Anthropic (Variante A) | ~290 | ~USD 2–5 |
| Groq (Variantes B + C) | ~580 | USD 0 (free tier) |

*Confirmar custo real em `evidence/baseline/_dry_run_report.md` após o dry-run.*

---

## Estrutura de saída

```
evidence/baseline/
├── <sha256-16>.json          # Uma evidência por execução
├── _dry_run_report.md        # Custo extrapolado vs real
├── summary.csv               # ASR por (variante, categoria, temperatura) — consumido pela Fase 8
├── manual_review_sample.csv  # Amostra para revisão humana (10% por estrato)
└── figures/
    ├── heatmap_temp_0.0.png
    ├── heatmap_temp_0.7.png
    └── asr_by_category.png
```
