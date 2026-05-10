from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tg_auth.adapters.database.base import BaseTable, IdentifableMixin, TimestampedMixin


class User(BaseTable, IdentifableMixin, TimestampedMixin):
    __tablename__ = "users"

    phone_number: Mapped[str | None] = mapped_column(
        String(32), unique=True, index=True, nullable=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    telegram_accounts: Mapped[list["TelegramAccount"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class TelegramAccount(BaseTable, IdentifableMixin, TimestampedMixin):
    __tablename__ = "telegram_accounts"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    picture: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user: Mapped[User] = relationship(back_populates="telegram_accounts", lazy="joined")
