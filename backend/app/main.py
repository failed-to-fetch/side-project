from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.db import get_engine
from app.core.redis_client import get_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()  # fail at startup, not on first request, if config is missing
    yield
    get_redis().close()
    get_engine().dispose()


# Everything lives under /api, the prefix the frontend's Caddy forwards here.
app = FastAPI(
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)
app.include_router(api_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
