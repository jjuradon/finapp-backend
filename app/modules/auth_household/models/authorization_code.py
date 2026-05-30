# app/modules/auth_household/models/authorization_code.py
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuthorizationCode(Base):
    """Single-use PKCE authorization code.

    Deleted immediately on exchange. used_at is set before deletion for audit trail.
    A background cleanup job (wired in M2) removes expired unused codes.
    """

    __tablename__ = "authorization_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[str] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[str] = mapped_column(server_default=text("now()"))

    # SHA-256 hex digest of the raw authorization code — never store the raw code
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # PKCE challenge: BASE64URL(SHA-256(code_verifier))
    code_challenge: Mapped[str] = mapped_column(String(128), nullable=False)
    code_challenge_method: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default=text("'S256'"),
    )

    client_id: Mapped[str] = mapped_column(String(100), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(String(512), nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # now() + 60 seconds set at insert time by the repository
    expires_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    # Set before deletion as audit trail; null = unused / not yet exchanged
    used_at: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "code_challenge_method = 'S256'",
            name="ck_auth_codes_method_s256",
        ),
        Index("idx_auth_codes_code_hash", "code_hash"),
        Index("idx_auth_codes_expires_at", "expires_at"),
    )
