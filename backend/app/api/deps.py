"""Shared FastAPI dependencies as Annotated types, so routes read as
`def route(db: DbSession, user: CurrentUser)`."""

from typing import Annotated

import redis
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.redis_client import get_redis
from app.features.auth.session import AuthUser, get_current_user

DbSession = Annotated[Session, Depends(get_db)]
RedisClient = Annotated[redis.Redis, Depends(get_redis)]
CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
