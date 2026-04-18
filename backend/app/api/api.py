from fastapi import APIRouter

from app.api.endpoints import auth, continents, countries, reports, chat, admin, contributors
from app.api.endpoints import stripe

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(continents.router, prefix="/continents", tags=["continents"])
api_router.include_router(countries.router, prefix="/countries", tags=["countries"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(contributors.router, prefix="/contributors", tags=["contributors"])
api_router.include_router(stripe.router, prefix="/stripe", tags=["stripe"])
