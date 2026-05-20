from fastapi import FastAPI

from app.infrastructure.web.middleware.audit_log import AuditLogMiddleware
from app.infrastructure.web.routers import auth, messages, orders, products, rag, refunds, users

app = FastAPI(title="PayChat Security Lab", version="0.3.0")

app.add_middleware(AuditLogMiddleware)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(users.router)
app.include_router(messages.router)
app.include_router(refunds.router)
app.include_router(rag.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
