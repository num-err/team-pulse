"""Authentication: verify Supabase Auth access tokens.

The frontend signs users in with Supabase Auth and sends the resulting
access token as `Authorization: Bearer <jwt>`. We verify it locally — no
network call per request:

- Projects using asymmetric signing keys (RS256/ES256, the current Supabase
  default) are verified against the project's public JWKS, fetched once and
  cached by PyJWKClient.
- Projects still on the legacy shared secret (HS256) are verified with
  SUPABASE_JWT_SECRET.

Either way we require a valid signature, an unexpired token, audience
"authenticated", and this project's issuer. Anything else is a 401.
"""
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

_AUDIENCE = "authenticated"
_ASYMMETRIC_ALGS = {"RS256", "ES256"}

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None


def _unauthorized(detail: str = "Invalid or missing access token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@lru_cache
def _jwks_client(supabase_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{supabase_url}/auth/v1/.well-known/jwks.json", cache_keys=True, lifespan=600)


def decode_access_token(token: str) -> dict:
    """Verify a Supabase access token and return its claims, or raise 401."""
    settings = get_settings()
    issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"

    try:
        alg = jwt.get_unverified_header(token).get("alg")
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise _unauthorized("HS256 tokens require SUPABASE_JWT_SECRET to be configured")
            key = settings.supabase_jwt_secret
        elif alg in _ASYMMETRIC_ALGS:
            if not settings.supabase_url:
                raise _unauthorized("SUPABASE_URL is not configured")
            key = _jwks_client(settings.supabase_url.rstrip("/")).get_signing_key_from_jwt(token).key
        else:
            # Includes "none" — never accepted.
            raise _unauthorized("Unsupported token algorithm")

        return jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience=_AUDIENCE,
            issuer=issuer,
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Access token expired") from exc
    except (jwt.PyJWTError, ValueError) as exc:
        raise _unauthorized() from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise _unauthorized()
    claims = decode_access_token(credentials.credentials)
    return CurrentUser(id=claims["sub"], email=claims.get("email"))
