"""SQLAlchemy database models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# pylint: disable=too-few-public-methods
class Base(DeclarativeBase):
    """Base class for all models."""


class Project(Base):
    """
    Represents a bot project that can be managed by H.A.M.A.L.
    
    Note: Runtime status (running/stopped) is NOT stored here.
    Status is tracked in-memory by ProcessManager.
    """
    # pylint: disable=too-few-public-methods
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    folder_path: Mapped[str] = mapped_column(Text, nullable=False)
    entrypoint: Mapped[str] = mapped_column(String(255), nullable=False, default="main.py")
    interpreter_path: Mapped[str] = mapped_column(Text, nullable=False)
    auto_start: Mapped[bool] = mapped_column(nullable=False, default=False)
    auto_restart: Mapped[bool] = mapped_column(nullable=False, default=False)
    dev_mode: Mapped[bool] = mapped_column(nullable=False, default=False)
    schedule_enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    schedule_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True) # HH:MM
    schedule_stop: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM
    schedule_days: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # 0,1,2,3...

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', auto_start={self.auto_start})>"
