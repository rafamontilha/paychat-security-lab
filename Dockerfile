FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
# --extra whitebox brings torch (CPU wheel) + transformers for the Fase 9 perplexity detector.
RUN uv sync --extra rag --extra agent --extra whitebox

COPY . .

# Pre-download GPT-2 weights so the first defended request doesn't fetch them at runtime
# (mid-matrix network failure would be worse). Non-fatal: runtime lazy-load is the fallback.
RUN uv run python -c "from transformers import AutoModelForCausalLM, AutoTokenizer; AutoModelForCausalLM.from_pretrained('gpt2'); AutoTokenizer.from_pretrained('gpt2')" \
    || echo "WARN: GPT-2 pre-download skipped (will lazy-load at runtime)"

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
