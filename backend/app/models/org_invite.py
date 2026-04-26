from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.org_membership import OrgRole


class InviteStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    revoked = "revoked"


class OrgInvite(Base):
    __tablename__ = "org_invites"
    __table_args__ = (
        UniqueConstraint("org_id", "email", "status", name="uq_org_invite_org_email_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))

    email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    role: Mapped[OrgRole] = mapped_column(Enum(OrgRole, name="org_role"), nullable=False, default=OrgRole.member)

    # Store SHA256 hash of the invite token.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    status: Mapped[InviteStatus] = mapped_column(
        Enum(InviteStatus, name="invite_status"), nullable=False, default=InviteStatus.pending
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    org = relationship("Organization", back_populates="invites")

