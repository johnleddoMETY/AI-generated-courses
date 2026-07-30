"""Supabase JWT verification for DRF.

Login/registration happens entirely on the frontend via supabase-js;
Django never sees a password, only the JWT Supabase already issued. This
class verifies that token and identifies the caller — it does not create
or store a User row. No per-resource ownership checks yet (see the
"Known gaps" section in backend/README.md); this is purely an
authenticated-or-not gate applied to every endpoint by default.
"""

from __future__ import annotations

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


class SupabaseJWTAuthentication(BaseAuthentication):
    def authenticate(self, request) -> tuple[SupabaseUser, str] | None:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None

        token = header.removeprefix("Bearer ").strip()
        try:
            claims = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed(f"Invalid Supabase token: {exc}") from exc

        return SupabaseUser(user_id=claims["sub"], email=claims.get("email")), token

    def authenticate_header(self, request) -> str:
        # Without this, DRF returns 403 instead of 401 for missing/invalid
        # credentials — this makes the "please authenticate" case correct.
        return "Bearer"
