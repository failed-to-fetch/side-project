"""Every feature router is registered here."""

from fastapi import APIRouter

from app.features.auth.router import router as auth_router
from app.features.integrations.github.router import router as github_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(github_router)
