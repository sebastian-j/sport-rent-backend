from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Instance


class HsqldbReservation(Base):
    __tablename__ = "hsqldb_reservations"

    source_position_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
    )
    instance_id: Mapped[int] = mapped_column(
        ForeignKey("instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    begin_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )
    source_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_hsqldb_reservations_instance_dates",
            "instance_id",
            "begin_at",
            "end_at",
        ),
    )

    instance: Mapped[Instance] = relationship()
