"""Supabase JWT verification for DRF.

Login/registration happen entirely on the frontend via supabase-js;
Django never sees a password, only the JWT Supabase already issued. This
class verifies that token and identifies the caller — it does not create
or store a User row. No per-resource ownership checks yet (see the
"Known gaps" section in backend/README.md); this is purely an
authenticated-or-not gate applied to every endpoint by default.

Current Supabase projects sign session tokens with an asymmetric key
(ES256) rotated via a JWKS endpoint, not a static shared secret — so
verification fetches Supabase's public signing key (via PyJWKClient,
which caches it) rather than checking against a local secret.
"""

from __future__ import annotations

import ssl
from functools import lru_cache

import certifi
import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class SupabaseUser:
    """Minimal, non-persisted stand-in for request.user.

    Carries only what's in the verified token claims.
    """

    is_authenticated = True

    def __init__(self, user_id: str, email: str | None) -> None:
        self.id = user_id
        self.email = email

    def __str__(self) -> str:
        return self.email or self.id


@lru_cache(maxsize=1)
def _get_jwks_client() -> jwt.PyJWKClient:
    # Explicit CA bundle: some Python installs (notably python.org builds on
    # macOS) don't wire up a working default trust store, which otherwise
    # fails JWKS fetches with "certificate verify failed."
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    return jwt.PyJWKClient(
        f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json",
        ssl_context=ssl_context,
    )


class SupabaseJWTAuthentication(BaseAuthentication):
    def authenticate(self, request) -> tuple[SupabaseUser, str] | None:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None

        token = header.removeprefix("Bearer ").strip()
        try:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed(f"Invalid Supabase token: {exc}") from exc

        return SupabaseUser(user_id=claims["sub"], email=claims.get("email")), token

    def authenticate_header(self, request) -> str:
        # Without this, DRF returns 403 instead of 401 for missing/invalid
        # credentials — this makes the "please authenticate" case correct.
        return "Bearer"
