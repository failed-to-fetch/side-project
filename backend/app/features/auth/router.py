from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.features.auth.session import AuthUser

router = APIRouter(tags=["auth"])


@router.get("/users/me", response_model=AuthUser)
def read_me(user: CurrentUser) -> AuthUser:
    return user
