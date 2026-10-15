"""Compatibility aggregation for workspace routers and legacy test imports."""

from fastapi import APIRouter

from app.api.routes.assets import router as assets_router
from app.api.routes.generations import download_export as download_export
from app.api.routes.generations import router as generations_router
from app.api.routes.projects import router as projects_router
from app.api.routes.storyboard import router as storyboard_router

router = APIRouter()
router.include_router(projects_router)
router.include_router(assets_router)
router.include_router(storyboard_router)
router.include_router(generations_router)
