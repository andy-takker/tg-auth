from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True, slots=True)
class TokenPair:
    """Access + refresh token pair returned by the auth endpoints.

    Shape mirrors the OAuth 2.0 token response so existing client libraries
    can consume it without translation.
    """

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 0  # seconds until the access_token expires
