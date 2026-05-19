from fastapi import FastAPI

app = FastAPI(title="PayChat Security Lab", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
