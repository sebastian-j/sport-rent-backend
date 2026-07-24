import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.tokens import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> int:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials

    try:
        payload = decode_access_token(token)

        subject = payload["sub"]
        session_id = payload["sid"]
        token_id = payload["jti"]

        if not all(isinstance(value, str) for value in (subject, session_id, token_id)):
            raise ValueError("Invalid access token claims")

        user_id = int(subject)

        if user_id <= 0:
            raise ValueError("Invalid user id")

        # Checks if Uuids can be created
        uuid.UUID(session_id)
        uuid.UUID(token_id)

        return user_id

    except jwt.InvalidTokenError, KeyError, TypeError, ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
