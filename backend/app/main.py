from contextlib import asynccontextmanager

import redis
from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.core.config import get_settings
from app.core.db import get_db, get_engine
from app.core.redis_client import get_redis
from app.core.security import DUMMY_HASH, hash_password, verify_password
from app.models import User
from app.routes_github_auth import router as github_auth_router
from app.schemas import LoginRequest, UserCreate, UserRead
from app.sessions import (
    COOKIE_NAME,
    create_session,
    delete_session,
    set_session_cookie,
)


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


@app.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    user = User(
        email=payload.email.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=UserRead)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
) -> User:
    user = db.scalar(
        select(User).where(func.lower(User.email) == payload.email.strip().lower())
    )
    stored_hash = user.password_hash if user and user.password_hash else DUMMY_HASH
    valid = verify_password(payload.password, stored_hash)
    if user is None or not user.password_hash or not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    set_session_cookie(response, create_session(r, user.id))
    return user


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session_id: str | None = Cookie(default=None, alias=COOKIE_NAME),
    r: redis.Redis = Depends(get_redis),
) -> None:
    if session_id:
        delete_session(r, session_id)
    response.delete_cookie(COOKIE_NAME)


@app.get("/users/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@app.get("/users/{user_id}", response_model=UserRead)
def get_user(user_id: int, current_user: User = Depends(get_current_user)) -> User:
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    return current_user