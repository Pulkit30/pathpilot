"""Shared dependencies injected into routes (and swapped out in tests)."""

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import Settings, get_settings
from backend.app.db import get_mongo_store
from backend.app.security import decode_token
from ml.kb import load_kb
from ml.recommender import Recommender


@lru_cache(maxsize=1)
def get_recommender():
    """Load the trained model once per process and reuse it for every request."""
    return Recommender.load()


def get_kb():
    return load_kb()


def get_user_store(settings: Settings = Depends(get_settings)):
    store = get_mongo_store(settings)
    if store is None or not settings.jwt_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Accounts are unavailable: MONGODB_URI and JWT_SECRET must be configured.")
    return store


_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
    store=Depends(get_user_store),
):
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in or session expired",
                                 headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    user_id = decode_token(credentials.credentials, settings)
    user = await store.get_by_id(user_id) if user_id else None
    if user is None:
        raise unauthorized
    return user
