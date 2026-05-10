"""Unit tests for the Telegram OIDC id_token verifier.

Signs tokens with a generated RS256 keypair (via the ``rsa_private_key``
fixture), feeds them to a fake ``PyJWKClient`` that returns the matching
public key, and exercises the real validation function.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import jwt
import pytest
from jwt import PyJWKClient

from tests.conftest import TEST_CLIENT_ID, TEST_ISSUER
from tg_auth.domains.use_cases.upsert_user_from_telegram import (
    _verify_telegram_id_token,
)


def test_happy_path_returns_claims(
    make_id_token: Callable[..., str], fake_jwks_client: PyJWKClient
) -> None:
    token = make_id_token()

    claims = _verify_telegram_id_token(
        id_token=token,
        jwks_client=fake_jwks_client,
        telegram_client_id=TEST_CLIENT_ID,
        telegram_issuer=TEST_ISSUER,
    )

    assert claims["sub"] == "1234567890"
    assert claims["aud"] == TEST_CLIENT_ID
    assert claims["iss"] == TEST_ISSUER
    assert claims["name"] == "Test User"


def test_empty_token_raises_value_error(fake_jwks_client: PyJWKClient) -> None:
    with pytest.raises(ValueError, match="Empty id_token"):
        _verify_telegram_id_token(
            id_token="",
            jwks_client=fake_jwks_client,
            telegram_client_id=TEST_CLIENT_ID,
            telegram_issuer=TEST_ISSUER,
        )


def test_wrong_audience_rejected(
    make_id_token: Callable[..., str], fake_jwks_client: PyJWKClient
) -> None:
    token = make_id_token(aud="someone-else")

    with pytest.raises(jwt.InvalidAudienceError):
        _verify_telegram_id_token(
            id_token=token,
            jwks_client=fake_jwks_client,
            telegram_client_id=TEST_CLIENT_ID,
            telegram_issuer=TEST_ISSUER,
        )


def test_wrong_issuer_rejected(
    make_id_token: Callable[..., str], fake_jwks_client: PyJWKClient
) -> None:
    token = make_id_token(iss="https://evil.example.com")

    with pytest.raises(jwt.InvalidIssuerError):
        _verify_telegram_id_token(
            id_token=token,
            jwks_client=fake_jwks_client,
            telegram_client_id=TEST_CLIENT_ID,
            telegram_issuer=TEST_ISSUER,
        )


def test_expired_token_rejected(
    make_id_token: Callable[..., str], fake_jwks_client: PyJWKClient
) -> None:
    token = make_id_token(iat=int(time.time()) - 7200, exp=int(time.time()) - 3600)

    with pytest.raises(jwt.ExpiredSignatureError):
        _verify_telegram_id_token(
            id_token=token,
            jwks_client=fake_jwks_client,
            telegram_client_id=TEST_CLIENT_ID,
            telegram_issuer=TEST_ISSUER,
        )


def test_missing_required_claim_rejected(
    rsa_private_key, fake_jwks_client: PyJWKClient
) -> None:
    # Hand-roll a token that's missing `sub`, which we explicitly require.
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": TEST_ISSUER,
            "aud": TEST_CLIENT_ID,
            "iat": now,
            "exp": now + 3600,
            # no `sub`
        },
        rsa_private_key,
        algorithm="RS256",
        headers={"kid": "test"},
    )

    with pytest.raises(jwt.MissingRequiredClaimError):
        _verify_telegram_id_token(
            id_token=token,
            jwks_client=fake_jwks_client,
            telegram_client_id=TEST_CLIENT_ID,
            telegram_issuer=TEST_ISSUER,
        )
