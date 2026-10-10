from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.api.deps import CurrentUser, DbSession, RedisClient
from app.core.config import get_settings
from app.features.integrations.github import service
from app.features.integrations.github.client import GitHubClient, get_github_client

# Connects a signed-in user's GitHub account for repository access.
router = APIRouter(prefix="/integrations/github", tags=["github"])

STATE_COOKIE = "oauth_state"
GitHub = Annotated[GitHubClient, Depends(get_github_client)]


def _redirect(path: str) -> RedirectResponse:
    resp = RedirectResponse(f"{get_settings().frontend_url}{path}", status_code=302)
    resp.delete_cookie(STATE_COOKIE)
    return resp


@router.get("/link")
def github_link(user: CurrentUser, r: RedisClient, github: GitHub) -> RedirectResponse:
    if not github.configured:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "GitHub is not configured."
        )
    url, state = service.start_link(r, github, user.id)
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie(
        STATE_COOKIE,
        state,
        max_age=service.STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=get_settings().cookie_secure,
    )
    return resp


@router.get("/callback")
def github_callback(
    db: DbSession,
    r: RedisClient,
    github: GitHub,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: Annotated[str | None, Cookie(alias=STATE_COOKIE)] = None,
) -> RedirectResponse:
    if error or not code or not state:
        return _redirect("/settings?error=github_denied")
    try:
        service.complete_link(
            db, r, github, code=code, state=state, browser_state=oauth_state
        )
    except service.LinkError as e:
        return _redirect(f"/settings?error={e.reason}")
    return _redirect("/settings?linked=github")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def unlink_github(user: CurrentUser, db: DbSession) -> None:
    if not service.unlink(db, user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "GitHub is not linked.")
