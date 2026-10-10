from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ProviderConnection(Base):
    """A user's grant to read repositories from a code host. Repo access only;
    sign-in is handled by Better Auth."""

    __tablename__ = "provider_connections"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id"),
        UniqueConstraint("user_id", "provider"),  # one connection per provider per user
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Better Auth "user".id. No foreign key: that table belongs to the auth service.
    user_id: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32))  # "github"
    provider_user_id: Mapped[str] = mapped_column(String(64))
    provider_login: Mapped[str | None] = mapped_column(String(255))
    access_token_enc: Mapped[str | None] = mapped_column(Text)  # encrypted
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)  # encrypted
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
