# app/modules/auth_household/models/user.py
import uuid

from sqlalchemy import Boolean, String, text
from sqlalchemy.dialects.postgresql import BYTEA, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    """User account — the central identity record for the application.

    password_hash is null for social-login users (Phase 2).
    ssn and date_of_birth are AES-256-GCM encrypted at the application layer.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[str] = mapped_column(
        server_default=text("now()"),
    )
    updated_at: Mapped[str] = mapped_column(
        server_default=text("now()"),
    )

    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(72), nullable=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # AES-256-GCM encrypted — Phase 2 collection; columns exist now per blueprint
    ssn: Mapped[bytes | None] = mapped_column(BYTEA, nullable=True)
    date_of_birth: Mapped[bytes | None] = mapped_column(BYTEA, nullable=True)
