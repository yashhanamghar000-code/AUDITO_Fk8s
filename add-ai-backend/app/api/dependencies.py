from types import SimpleNamespace

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import settings
from app.container import Container, build_container

bearer_scheme = HTTPBearer()


def get_container() -> Container:
    return build_container()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> SimpleNamespace:

    try:
        r = httpx.post(
            f"{settings.auth_service_url}/verify",
            json={"token": credentials.credentials},
            timeout=10,
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth service unreachable")
    if r.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    data = r.json()
    return SimpleNamespace(id=data["user_id"], name=data["name"], email=data["email"])