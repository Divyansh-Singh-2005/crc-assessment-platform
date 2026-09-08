"""NIST CSF 2.0 hierarchy and control-to-subcategory mappings."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.control import Control


class Framework(Base, TimestampMixin):
    __tablename__ = "frameworks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    functions: Mapped[list["FrameworkFunction"]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )


class FrameworkFunction(Base):
    """Govern, Identify, Protect, Detect, Respond, Recover."""

    __tablename__ = "framework_functions"

    id: Mapped[int] = mapped_column(primary_key=True)
    framework_id: Mapped[int] = mapped_column(
        ForeignKey("frameworks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(4), nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    framework: Mapped["Framework"] = relationship(back_populates="functions")
    categories: Mapped[list["FrameworkCategory"]] = relationship(
        back_populates="function", cascade="all, delete-orphan"
    )


class FrameworkCategory(Base):
    """For example PR.AA - Identity Management, Authentication and Access Control."""

    __tablename__ = "framework_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    function_id: Mapped[int] = mapped_column(
        ForeignKey("framework_functions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    function: Mapped["FrameworkFunction"] = relationship(back_populates="categories")
    subcategories: Mapped[list["FrameworkSubcategory"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class FrameworkSubcategory(Base):
    """For example PR.AA-03 - Users, services and hardware are authenticated."""

    __tablename__ = "framework_subcategories"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("framework_categories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    category: Mapped["FrameworkCategory"] = relationship(back_populates="subcategories")
    mappings: Mapped[list["FrameworkMapping"]] = relationship(
        back_populates="subcategory", cascade="all, delete-orphan"
    )


class FrameworkMapping(Base):
    """Many-to-many link between an organisational control and a CSF subcategory."""

    __tablename__ = "framework_mappings"

    control_id: Mapped[int] = mapped_column(
        ForeignKey("controls.id", ondelete="CASCADE"), primary_key=True
    )
    subcategory_id: Mapped[int] = mapped_column(
        ForeignKey("framework_subcategories.id", ondelete="CASCADE"), primary_key=True
    )

    control: Mapped["Control"] = relationship(back_populates="framework_mappings")
    subcategory: Mapped["FrameworkSubcategory"] = relationship(back_populates="mappings")
