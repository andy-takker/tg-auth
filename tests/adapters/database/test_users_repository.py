"""Integration tests for ``UsersRepository.upsert_user_from_claims`` against
a real SQLite (in-tmp) database.

Three branches:
1. Brand new user with no existing telegram_account.
2. Returning user — telegram_id already linked, mutable fields refresh.
3. Phone-based linking — telegram_account is new, but a User with the same
   phone already exists (e.g. registered earlier via SMS).
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tg_auth.adapters.database.repositories.users import UsersRepository
from tg_auth.adapters.database.tables import TelegramAccount, User
from tg_auth.adapters.database.uow import SqlalchemyUow


@pytest.fixture
def repo(db_session: AsyncSession) -> UsersRepository:
    """A repository wired against a fake UoW that just hands out the same
    session. Lets us call repository methods without going through
    ``async with uow:``."""

    class _DirectUow:
        @property
        def session(self) -> AsyncSession:
            return db_session

    # The repository only reads ``uow.session``; cast for type-shape.
    return UsersRepository(uow=_DirectUow())  # type: ignore[arg-type]


def _claims(**overrides: Any) -> dict[str, Any]:
    base = {
        "sub": "1234567890",
        "id": 1234567890,
        "name": "Test User",
        "preferred_username": "testuser",
        "picture": "https://example.com/pic.jpg",
        "phone_number": "+15551234567",
    }
    base.update(overrides)
    return base


async def test_creates_user_and_telegram_account_for_new_login(
    repo: UsersRepository, db_session: AsyncSession
) -> None:
    user = await repo.upsert_user_from_claims(_claims())
    await db_session.commit()

    assert user.phone_number == "+15551234567"
    assert user.name == "Test User"

    tg_accs = (
        (
            await db_session.execute(
                select(TelegramAccount).where(TelegramAccount.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(tg_accs) == 1
    assert tg_accs[0].telegram_id == 1234567890
    assert tg_accs[0].username == "testuser"
    assert tg_accs[0].phone_number == "+15551234567"


async def test_returning_user_updates_mutable_fields(
    repo: UsersRepository, db_session: AsyncSession
) -> None:
    # First login.
    await repo.upsert_user_from_claims(_claims())
    await db_session.commit()

    # Second login: same telegram_id, new username and picture.
    user2 = await repo.upsert_user_from_claims(
        _claims(preferred_username="renamed", picture="https://example.com/new.jpg")
    )
    await db_session.commit()

    # No new user / account rows.
    users = (await db_session.execute(select(User))).scalars().all()
    accs = (await db_session.execute(select(TelegramAccount))).scalars().all()
    assert len(users) == 1
    assert len(accs) == 1
    assert accs[0].username == "renamed"
    assert accs[0].picture == "https://example.com/new.jpg"
    assert user2.id == users[0].id


async def test_links_to_existing_user_by_phone(
    repo: UsersRepository, db_session: AsyncSession
) -> None:
    # Pre-existing user (e.g. registered via SMS earlier).
    existing = User(phone_number="+15551234567", name="Existing")
    db_session.add(existing)
    await db_session.flush()
    await db_session.commit()

    # Telegram login arrives with the same phone.
    user = await repo.upsert_user_from_claims(_claims())
    await db_session.commit()

    # Same user row reused, no duplicate.
    assert user.id == existing.id
    users = (await db_session.execute(select(User))).scalars().all()
    assert len(users) == 1

    accs = (
        (
            await db_session.execute(
                select(TelegramAccount).where(TelegramAccount.user_id == existing.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(accs) == 1


async def test_phone_backfilled_when_first_login_lacked_it(
    repo: UsersRepository, db_session: AsyncSession
) -> None:
    # First login: user didn't grant `phone` scope.
    await repo.upsert_user_from_claims(_claims(phone_number=None))
    await db_session.commit()

    user = (await db_session.execute(select(User))).scalar_one()
    assert user.phone_number is None

    # Second login: user now grants phone.
    await repo.upsert_user_from_claims(_claims())
    await db_session.commit()

    await db_session.refresh(user)
    assert user.phone_number == "+15551234567"


async def test_uow_lifecycle_smoke(db_engine) -> None:
    """SqlalchemyUow opens and closes a session via async context manager."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    uow = SqlalchemyUow(session_factory=factory)

    async with uow:
        assert uow.session is not None
