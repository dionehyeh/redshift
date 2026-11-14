import secrets
from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.config import settings


class ClerkConfigurationError(RuntimeError):
    pass


@lru_cache(maxsize=2)
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url)


def decode_clerk_token(token: str) -> dict:
    if not settings.clerk_issuer or not settings.clerk_jwks_url:
        raise ClerkConfigurationError("Set CLERK_ISSUER and CLERK_JWKS_URL")

    signing_key = _jwks_client(settings.clerk_jwks_url).get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=settings.clerk_issuer,
        options={"require": ["exp", "iat", "sub"]},
    )
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise jwt.InvalidTokenError("Clerk token is missing a subject")
    authorized_party = claims.get("azp")
    if not authorized_party or authorized_party not in settings.allowed_origins:
        raise jwt.InvalidTokenError("Clerk token was issued for an untrusted origin")
    return claims


def new_share_token() -> str:
    return secrets.token_urlsafe(24)
