"""Accounts: register, log in, and 'who am I'."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.config import Settings, get_settings
from backend.app.db import EmailTakenError
from backend.app.deps import get_current_user, get_store
from backend.app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from backend.app.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _public(user):
    return {"id": user["id"], "email": user["email"], "name": user["name"]}


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, store=Depends(get_store),
                   settings: Settings = Depends(get_settings)):
    try:
        user = await store.create_user(body.email.lower(), body.name.strip(), hash_password(body.password))
    except EmailTakenError:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists") from None
    return {"access_token": create_token(user["id"], settings), "user": _public(user)}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, store=Depends(get_store), settings: Settings = Depends(get_settings)):
    user = await store.get_user_by_email(body.email.lower())
    # Same message for "no such user" and "wrong password" so emails can't be probed.
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return {"access_token": create_token(user["id"], settings), "user": _public(user)}


@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return _public(user)
