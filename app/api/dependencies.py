from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.auth_helpers import unauthorized
from app.core.tokens import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> int:
    if credentials is None:
        raise unauthorized(
            "Authentication credentials were not provided",
            bearer_challenge=True,
        )
    token = credentials.credentials

    try:
        claims = decode_access_token(token)
        return claims.user_id
    except jwt.InvalidTokenError:
        raise unauthorized("Invalid token", bearer_challenge=True) from None
