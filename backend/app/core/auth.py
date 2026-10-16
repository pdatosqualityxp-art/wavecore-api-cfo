import logging
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool
from supabase import create_client
from supabase_auth.errors import AuthApiError
from supabase_auth.types import User

from app.core.config import settings


logger = logging.getLogger(__name__)
_bearer_scheme = HTTPBearer(auto_error=False)
_supabase_auth = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key,
).auth


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
) -> User:
    """Validate the Supabase access token and return its user (guests included)."""
    if credentials is None or not credentials.credentials.strip():
        raise _unauthorized("A valid Bearer access token is required")

    try:
        response = await run_in_threadpool(
            _supabase_auth.get_user, credentials.credentials
        )
    except AuthApiError as error:
        raise _unauthorized("The access token is invalid or has expired") from error
    except Exception as error:
        logger.exception("Supabase Auth could not validate the access token")
        raise HTTPException(
            status_code=503,
            detail="The authentication service is unavailable",
        ) from error

    if response is None or response.user is None:
        raise _unauthorized("The access token is invalid or has expired")
    return response.user


async def get_registered_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Like get_current_user but rejects anonymous (guest) sessions."""
    if user.is_anonymous:
        raise HTTPException(
            status_code=403,
            detail="A registered user is required for this operation",
        )
    return user
