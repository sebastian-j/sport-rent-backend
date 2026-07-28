from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
    )
    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    first_line: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    second_line: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    postal_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    nip: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    default_for_user: Mapped[User | None] = relationship(
        back_populates="default_address",
        uselist=False,
    )


if TYPE_CHECKING:
    from app.models.user import User
