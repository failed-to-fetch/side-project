from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.auth import AuthUser, get_current_user
from app.core.config import get_settings
from app.core.db import get_engine
from app.core.redis_client import get_redis
from app.routes_github_auth import router as github_auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()  # fail at startup, not on first request, if config is missing
    yield
    get_redis().close()
    get_engine().dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(github_auth_router)


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.get("/users/me", response_model=AuthUser)
def read_me(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
    return current_user
