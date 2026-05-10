import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, Uuid
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declarative_mixin,
    declared_attr,
    mapped_column,
)

convention = {
    "all_column_names": lambda constraint, table: "_".join(
        [column.name for column in constraint.columns.values()],
    ),
    "ix": "ix__%(table_name)s__%(all_column_names)s",
    "uq": "uq__%(table_name)s__%(all_column_names)s",
    "ck": "ck__%(table_name)s__%(constraint_name)s",
    "fk": "fk__%(table_name)s__%(all_column_names)s__%(referred_table_name)s",
    "pk": "pk__%(table_name)s",
}


class BaseTable(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)  # type: ignore[arg-type]


def now_with_tz() -> datetime:
    return datetime.now(UTC)


@declarative_mixin
class CreatedAtMixin:
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            default=now_with_tz,
        )


@declarative_mixin
class UpdatedAtMixin:
    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            default=now_with_tz,
            onupdate=now_with_tz,
        )


@declarative_mixin
class DeletedAtMixin:
    @declared_attr
    def deleted_at(cls) -> Mapped[datetime | None]:
        return mapped_column(
            DateTime(timezone=True),
            nullable=True,
        )


@declarative_mixin
class TimestampedMixin(CreatedAtMixin, UpdatedAtMixin, DeletedAtMixin): ...


@declarative_mixin
class IdentifableMixin:
    @declared_attr
    def id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            Uuid,
            primary_key=True,
            default=uuid.uuid4,
        )
