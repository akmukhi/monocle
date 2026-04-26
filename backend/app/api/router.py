from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.orgs import router as orgs_router
from app.api.routes.costs import router as costs_router
from app.api.routes.ai import router as ai_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(orgs_router, tags=["orgs"])
api_router.include_router(costs_router, tags=["costs"])
api_router.include_router(ai_router, tags=["ai"])

