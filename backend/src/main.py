import redis
from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.auth import get_current_user
from src.database import get_db
from src.models import User
from src.redis_client import get_redis
from src.schemas import LoginRequest, UserCreate, UserRead
from src.security import DUMMY_HASH, hash_password, verify_password
from src.sessions import (
    COOKIE_NAME,
    COOKIE_SECURE,
    SESSION_TTL_SECONDS,
    create_session,
    delete_session,
)

app = FastAPI()
from src.routes_github_auth import router as github_auth_router

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

    token = create_session(r, user.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )
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