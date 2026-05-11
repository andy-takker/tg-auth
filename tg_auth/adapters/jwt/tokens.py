"""HMAC-SHA256 JWT issuer/validator backing :class:`ITokenIssuer`.

Tokens carry:
- ``sub``  — application user UUID, as a string.
- ``type`` — ``access`` or ``refresh``. The two are otherwise identical and
  the type claim is what stops a refresh token from being used as an access
  token (and vice versa).
- ``iat`` / ``exp`` — issued / expiry timestamps, seconds.
- ``iss`` — set from config; verified on decode.
- ``jti`` — random per-token id; not used yet, but in place for a future
  revocation list.
"""

import secrets
import time
from uuid import UUID

import jwt

from tg_auth.application.config import JwtConfig
from tg_auth.domains.entities.tokens import TokenPair
from tg_auth.domains.entities.user import UserID
from tg_auth.domains.interfaces.tokens import InvalidTokenError, ITokenIssuer

ACCESS_TYPE = "access"
REFRESH_TYPE = "refresh"


class JwtTokenIssuer(ITokenIssuer):
    def __init__(self, config: JwtConfig) -> None:
        self._config = config

    def issue_pair(self, user_id: UserID) -> TokenPair:
        return TokenPair(
            access_token=self._encode(
                user_id, ACCESS_TYPE, self._config.access_ttl_seconds
            ),
            refresh_token=self._encode(
                user_id, REFRESH_TYPE, self._config.refresh_ttl_seconds
            ),
            expires_in=self._config.access_ttl_seconds,
        )

    def validate_access(self, token: str) -> UserID:
        return self._decode(token, expected_type=ACCESS_TYPE)

    def validate_refresh(self, token: str) -> UserID:
        return self._decode(token, expected_type=REFRESH_TYPE)

    def _encode(self, user_id: UserID, token_type: str, ttl_seconds: int) -> str:
        now = int(time.time())
        return jwt.encode(
            {
                "sub": str(user_id),
                "iss": self._config.issuer,
                "type": token_type,
                "iat": now,
                "exp": now + ttl_seconds,
                "jti": secrets.token_urlsafe(16),
            },
            self._config.secret,
            algorithm=self._config.algorithm,
        )

    def _decode(self, token: str, *, expected_type: str) -> UserID:
        if not token:
            raise InvalidTokenError("Empty token")

        try:
            claims = jwt.decode(
                token,
                self._config.secret,
                algorithms=[self._config.algorithm],
                issuer=self._config.issuer,
                options={"require": ["sub", "iss", "iat", "exp", "type"]},
            )
        except jwt.PyJWTError as e:
            raise InvalidTokenError(str(e)) from e

        if claims.get("type") != expected_type:
            raise InvalidTokenError(
                f"Expected token type {expected_type!r}, got {claims.get('type')!r}"
            )

        try:
            return UserID(UUID(str(claims["sub"])))
        except ValueError as e:
            raise InvalidTokenError(f"Invalid sub claim: {e}") from e
