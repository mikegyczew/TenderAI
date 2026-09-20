import hashlib
import hmac
import logging
import os
import secrets
import time

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


logger = logging.getLogger("tenderai.auth")
COOKIE_NAME = "tenderai_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "TenderPZU")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "TenderPZU#2026")
AUTH_SECRET = os.getenv("AUTH_SECRET", AUTH_PASSWORD)


def _signature(value: str) -> str:
    return hmac.new(
        AUTH_SECRET.encode(),
        value.encode(),
        hashlib.sha256,
    ).hexdigest()


def create_session() -> str:
    payload = f"{secrets.token_urlsafe(32)}:{int(time.time())}"
    return f"{payload}.{_signature(payload)}"


def is_valid_session(value: str | None) -> bool:
    if not value or "." not in value:
        return False

    payload, signature = value.rsplit(".", 1)
    try:
        _, created_at = payload.rsplit(":", 1)
        is_fresh = time.time() - int(created_at) <= SESSION_TTL_SECONDS
    except (ValueError, TypeError):
        return False

    return is_fresh and hmac.compare_digest(signature, _signature(payload))


def require_authentication(request: Request) -> None:
    if not is_valid_session(request.cookies.get(COOKIE_NAME)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wymagane logowanie.",
        )


def login(username: str, password: str) -> JSONResponse:
    if not (
        hmac.compare_digest(username, AUTH_USERNAME)
        and hmac.compare_digest(password, AUTH_PASSWORD)
    ):
        logger.warning("Nieudana próba logowania dla użytkownika %s", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy login lub hasło.",
        )

    response = JSONResponse({"authenticated": True, "username": AUTH_USERNAME})
    response.set_cookie(
        COOKIE_NAME,
        create_session(),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=SESSION_TTL_SECONDS,
    )
    logger.info("Użytkownik %s zalogował się", AUTH_USERNAME)
    return response
