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


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)


@app.get("/")
def root():
    return {"message": "Backend is running"}
