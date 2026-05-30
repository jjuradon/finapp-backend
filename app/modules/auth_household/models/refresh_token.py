# app/modules/auth_household/models/refresh_token.py
import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RefreshToken(Base):
    """Stores information about issued OAuth2/OIDC refresh tokens.

    Includes token_hash (SHA-256) and support for refresh token rotation family tracking.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[str] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[str] = mapped_column(server_default=text("now()"))

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # SHA-256 hex digest of the raw refresh token
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # UUID identifying the family of refresh tokens for rotation detection
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    # Mark the family as revoked (e.g. if a token is reused)
    is_family_revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    expires_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (Index("idx_refresh_tokens_token_hash", "token_hash"),)
