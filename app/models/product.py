from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(255), nullable=False)

    products: Mapped[list[Product]] = relationship(
        back_populates="category", cascade="all, delete-orphan", passive_deletes=True
    )


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    product: Mapped[Product] = relationship(back_populates="favorites")
    user: Mapped[User] = relationship()


class InstanceStatus(enum.Enum):
    AVAILABLE = "AVAILABLE"
    MAINTENANCE = "MAINTENANCE"
    BROKEN = "BROKEN"
    RETIRED = "RETIRED"


class Instance(Base):
    __tablename__ = "instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[InstanceStatus | None] = mapped_column(
        Enum(InstanceStatus), server_default="AVAILABLE", nullable=False
    )
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)

    product: Mapped[Product] = relationship(back_populates="instances")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    slug: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    meta_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visibility_status: Mapped[bool | None] = mapped_column(Boolean, nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (CheckConstraint("price > 0", name="check_price_positive"),)

    category: Mapped[Category | None] = relationship(back_populates="products")
    images: Mapped[list[ProductImage]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    sizes: Mapped[list[ProductSize]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    instances: Mapped[list[Instance]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    favorites: Mapped[list[Favorite]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    image: Mapped[str | None] = mapped_column(String(255), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=False)
    display_order: Mapped[int | None] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "product_id", "display_order", name="uix_product_display_order"
        ),
    )

    product: Mapped[Product] = relationship(back_populates="images")


class ProductSize(Base):
    __tablename__ = "product_sizes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    size: Mapped[str | None] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("product_id", "size", name="uix_product_size"),)

    product: Mapped[Product | None] = relationship(back_populates="sizes")
