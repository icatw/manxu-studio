from fastapi import APIRouter

from app.api.routes.assets import router as assets_router
from app.api.routes.auth import router as auth_router
from app.api.routes.generations import router as generations_router
from app.api.routes.projects import router as projects_router
from app.api.routes.storyboard import router as storyboard_router
from app.api.routes.system import router as system_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(system_router)
api_router.include_router(projects_router)
api_router.include_router(assets_router)
api_router.include_router(storyboard_router)
api_router.include_router(generations_router)
