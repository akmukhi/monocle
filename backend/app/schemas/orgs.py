from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime


class MembershipOut(BaseModel):
    org_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    created_at: datetime


class InviteCreateRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(owner|member)$")
    expires_in_hours: int = Field(default=72, ge=1, le=24 * 30)


class InviteCreatedResponse(BaseModel):
    invite_id: uuid.UUID
    email: EmailStr
    role: str
    expires_at: datetime
    invite_token: str


class AcceptInviteRequest(BaseModel):
    token: str = Field(min_length=10, max_length=500)

