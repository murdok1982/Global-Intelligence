"""
ASGI middleware that appends an audit event for every classified
endpoint hit.

For requests under ``/api/v1/classified/*`` the middleware:

1. Records actor IP, user agent and Authorization-derived user id
   (best-effort decode, never raises on bad tokens).
2. Lets the endpoint run; if the handler set ``request.state.audit_event``
   (a dict), that payload is used; otherwise we generate a generic
   entry with the method + path as event_type.
3. Maps the HTTP status code to ``success`` / ``denied`` / ``error``.
4. Writes one append-only row to the audit log on a fresh DB session
   so the chain is durable even if the endpoint's own transaction
   was rolled back.

The middleware NEVER reads the request body and NEVER stores the
response body. Only metadata reaches the audit table.
"""

from __future__ import annotations

import logging
from typing import Optional

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.audit import audit_service

logger = logging.getLogger(__name__)


_CLASSIFIED_PREFIX = f"{settings.API_V1_STR}/classified"


def _extract_user_id(request: Request) -> Optional[str]:
    """Best-effort sub claim extraction from the Authorization header.

    Returns ``None`` for missing / malformed / expired tokens — the
    middleware records the event anyway so failed auth attempts are
    auditable.
    """
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},  # we still want to audit expired calls
        )
        sub = payload.get("sub")
        return str(sub) if sub else None
    except Exception:
        return None


def _outcome_for_status(status_code: int) -> str:
    if status_code >= 500:
        return "error"
    if status_code >= 400:
        return "denied"
    return "success"


class AuditMiddleware(BaseHTTPMiddleware):
    """Append an audit row for every classified request."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith(_CLASSIFIED_PREFIX):
            return await call_next(request)

        # Run the actual endpoint first so it can populate
        # request.state.audit_event with richer context.
        response: Response = await call_next(request)

        try:
            payload = getattr(request.state, "audit_event", None) or {}
            event_type = payload.get(
                "event_type",
                f"classified.{request.method.lower()}.{path}",
            )
            metadata = dict(payload.get("metadata") or {})
            metadata.setdefault("status_code", response.status_code)
            metadata.setdefault("method", request.method)
            metadata.setdefault("path", path)

            actor_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            user_id = payload.get("actor_user_id") or _extract_user_id(request)

            outcome = payload.get("outcome") or _outcome_for_status(response.status_code)

            async with AsyncSessionLocal() as db:
                await audit_service.record(
                    db,
                    event_type=event_type,
                    actor_user_id=user_id,
                    actor_ip=actor_ip,
                    actor_user_agent=user_agent,
                    resource_type=payload.get("resource_type"),
                    resource_id=payload.get("resource_id"),
                    classification=payload.get("classification"),
                    org_id=payload.get("org_id"),
                    outcome=outcome,
                    metadata=metadata,
                )
                await db.commit()
        except Exception as exc:  # pragma: no cover - defensive
            # We deliberately swallow audit failures so they cannot
            # turn into an availability incident, but they must be
            # loud in the logs so operators see drift.
            logger.error(
                "audit_middleware.write_failed path=%s status=%s err=%r",
                path,
                response.status_code,
                exc,
            )

        return response


__all__ = ["AuditMiddleware"]
