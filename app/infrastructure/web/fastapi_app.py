from fastapi import FastAPI

from app.infrastructure.web.middleware.audit_log import AuditLogMiddleware
from app.infrastructure.web.routers import (
    agent,
    auth,
    messages,
    orders,
    products,
    rag,
    refunds,
    users,
)

app = FastAPI(title="PayChat Security Lab", version="0.6.0")

app.add_middleware(AuditLogMiddleware)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(users.router)
app.include_router(messages.router)
app.include_router(refunds.router)
app.include_router(rag.router)
app.include_router(agent.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/deep")
def health_deep() -> dict[str, object]:
    """Extended health check that probes downstream services used by Variant C."""
    import os

    import httpx

    presidio_url = os.environ.get("PRESIDIO_URL", "http://presidio:3000")
    try:
        r = httpx.get(f"{presidio_url}/health", timeout=3.0)
        presidio_ok = r.status_code == 200
    except Exception:
        presidio_ok = False

    overall = "ok" if presidio_ok else "degraded"
    return {
        "status": overall,
        "services": {
            "presidio": "ok" if presidio_ok else "unavailable",
        },
    }
