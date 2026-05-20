import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.infrastructure.persistence.database import get_session_factory
from app.infrastructure.persistence.models import AuditLog

_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        # Read body before passing to handler (BaseHTTPMiddleware buffers it)
        try:
            raw = await request.body()
            request_body = raw.decode("utf-8", errors="replace")[:500] or None
        except Exception:
            request_body = None

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        actor = getattr(request.state, "actor", None)

        factory = get_session_factory()
        db = factory()
        try:
            log = AuditLog(
                session_token=actor.get("session_token") if actor else None,
                user_id=actor.get("user_id") if actor else None,
                role=actor.get("role") if actor else None,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                request_body=request_body,
                response_time_ms=elapsed_ms,
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        return response
