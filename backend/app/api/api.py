"""
API surface split between PUBLIC and CLASSIFIED scopes.

* ``public_router``  — anything mountable on ``/api/v1/public``.
  No authentication is enforced at the router level; individual
  endpoints (e.g. login) keep their own constraints.

* ``classified_router`` — mounted on ``/api/v1/classified`` with a
  hard ``require_mfa_verified_user`` dependency. Every endpoint
  inside this router is reachable only by authenticated users with
  MFA verified AND at least RESTRICTED clearance.

The legacy ``api_router`` is kept for backwards compatibility — it
aggregates both scopes without authentication enforcement so old
clients that hit ``/api/v1/<...>`` continue to work during the
migration.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps_classified import require_mfa_verified_user
from app.api.endpoints import (
    admin,
    agents,
    auth,
    chat,
    continents,
    contributors,
    countries,
    export,
    military,
    reports,
    signing,
)


# --- Public scope -----------------------------------------------------------
public_router = APIRouter()
public_router.include_router(auth.router, prefix="/auth", tags=["auth"])
public_router.include_router(continents.router, prefix="/continents", tags=["continents"])
public_router.include_router(countries.router, prefix="/countries", tags=["countries"])
public_router.include_router(military.router, prefix="/military", tags=["military"])
public_router.include_router(signing.public_router, prefix="/signing", tags=["signing"])


# --- Classified scope -------------------------------------------------------
classified_router = APIRouter(
    dependencies=[Depends(require_mfa_verified_user)],
)
classified_router.include_router(reports.router, prefix="/reports", tags=["reports"])
classified_router.include_router(chat.router, prefix="/chat", tags=["chat"])
classified_router.include_router(admin.router, prefix="/admin", tags=["admin"])
classified_router.include_router(export.router, prefix="/export", tags=["export"])
classified_router.include_router(
    contributors.router, prefix="/contributors", tags=["contributors"]
)
classified_router.include_router(
    signing.admin_router, prefix="/admin/signing", tags=["signing"]
)
classified_router.include_router(agents.router, prefix="/agents", tags=["agents"])


# --- Legacy aggregator (with MFA enforcement for classified endpoints) ----
# Kept for backwards compatibility. Classified endpoints require MFA.
api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(continents.router, prefix="/continents", tags=["continents"])
api_router.include_router(countries.router, prefix="/countries", tags=["countries"])
api_router.include_router(military.router, prefix="/military", tags=["military"])

# Classified endpoints in legacy router require MFA
api_router_classified = APIRouter(
    dependencies=[Depends(require_mfa_verified_user)],
)
api_router_classified.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router_classified.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router_classified.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router_classified.include_router(export.router, prefix="/export", tags=["export"])
api_router_classified.include_router(
    contributors.router, prefix="/contributors", tags=["contributors"]
)
api_router_classified.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(api_router_classified)


__all__ = ["public_router", "classified_router", "api_router"]
