import redis
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.redis_client import get_redis
from app.models import User
from app.sessions import COOKIE_NAME, get_session_user_id


def get_current_user(
    session_id: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
    )
    if not session_id:
        raise unauthorized
    user_id = get_session_user_id(r, session_id)
    if user_id is None:
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user