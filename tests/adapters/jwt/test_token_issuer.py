"""Unit tests for ``JwtTokenIssuer``.

We instantiate the issuer directly with a tiny config — no Dishka, no app —
to keep the test focused on the encode/decode roundtrip and the type-claim
discrimination between access and refresh.
"""

from __future__ import annotations

import time
from uuid import uuid4

import jwt
import pytest

from tg_auth.adapters.jwt.tokens import ACCESS_TYPE, REFRESH_TYPE, JwtTokenIssuer
from tg_auth.application.config import JwtConfig
from tg_auth.domains.interfaces.tokens import InvalidTokenError


@pytest.fixture
def issuer() -> JwtTokenIssuer:
    return JwtTokenIssuer(
        config=JwtConfig(
            secret="unit-test-secret",
            algorithm="HS256",
            issuer="tg-auth-test",
            access_ttl_seconds=900,
            refresh_ttl_seconds=86400,
        )
    )


def test_issue_pair_returns_two_distinct_tokens(issuer: JwtTokenIssuer) -> None:
    user_id = uuid4()

    pair = issuer.issue_pair(user_id)

    assert pair.access_token
    assert pair.refresh_token
    assert pair.access_token != pair.refresh_token
    assert pair.token_type == "Bearer"
    assert pair.expires_in == 900


def test_validate_access_returns_user_id(issuer: JwtTokenIssuer) -> None:
    user_id = uuid4()
    pair = issuer.issue_pair(user_id)

    assert issuer.validate_access(pair.access_token) == user_id


def test_validate_refresh_returns_user_id(issuer: JwtTokenIssuer) -> None:
    user_id = uuid4()
    pair = issuer.issue_pair(user_id)

    assert issuer.validate_refresh(pair.refresh_token) == user_id


def test_access_token_rejected_as_refresh(issuer: JwtTokenIssuer) -> None:
    pair = issuer.issue_pair(uuid4())

    with pytest.raises(InvalidTokenError, match="Expected token type 'refresh'"):
        issuer.validate_refresh(pair.access_token)


def test_refresh_token_rejected_as_access(issuer: JwtTokenIssuer) -> None:
    pair = issuer.issue_pair(uuid4())

    with pytest.raises(InvalidTokenError, match="Expected token type 'access'"):
        issuer.validate_access(pair.refresh_token)


def test_empty_token_rejected(issuer: JwtTokenIssuer) -> None:
    with pytest.raises(InvalidTokenError, match="Empty token"):
        issuer.validate_access("")


def test_garbage_token_rejected(issuer: JwtTokenIssuer) -> None:
    with pytest.raises(InvalidTokenError):
        issuer.validate_access("not-a-jwt")


def test_expired_token_rejected(issuer: JwtTokenIssuer) -> None:
    # Hand-roll an expired access token so we don't have to sleep.
    now = int(time.time())
    expired = jwt.encode(
        {
            "sub": str(uuid4()),
            "iss": "tg-auth-test",
            "type": ACCESS_TYPE,
            "iat": now - 7200,
            "exp": now - 3600,
            "jti": "x",
        },
        "unit-test-secret",
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        issuer.validate_access(expired)


def test_token_signed_with_other_secret_rejected(issuer: JwtTokenIssuer) -> None:
    now = int(time.time())
    forged = jwt.encode(
        {
            "sub": str(uuid4()),
            "iss": "tg-auth-test",
            "type": ACCESS_TYPE,
            "iat": now,
            "exp": now + 3600,
            "jti": "x",
        },
        "different-secret",
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        issuer.validate_access(forged)


def test_token_with_wrong_issuer_rejected(issuer: JwtTokenIssuer) -> None:
    now = int(time.time())
    bad_iss = jwt.encode(
        {
            "sub": str(uuid4()),
            "iss": "evil",
            "type": REFRESH_TYPE,
            "iat": now,
            "exp": now + 3600,
            "jti": "x",
        },
        "unit-test-secret",
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        issuer.validate_refresh(bad_iss)
