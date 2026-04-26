from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user
from app.core.security import generate_invite_token, hash_token
from app.db.session import get_db
from app.models.org_invite import InviteStatus, OrgInvite
from app.models.org_membership import OrgMembership, OrgRole
from app.models.organization import Organization
from app.models.user import User
from app.schemas.orgs import (
    AcceptInviteRequest,
    InviteCreateRequest,
    InviteCreatedResponse,
    MembershipOut,
    OrganizationOut,
)

router = APIRouter(prefix="/orgs")


@router.get("/me", response_model=list[OrganizationOut])
async def my_orgs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrganizationOut]:
    res = await db.execute(
        select(Organization)
        .join(OrgMembership, OrgMembership.org_id == Organization.id)
        .where(OrgMembership.user_id == current_user.id)
        .order_by(Organization.created_at.asc())
    )
    return list(res.scalars().all())


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_org(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationOut:
    org = Organization(name=name)
    membership = OrgMembership(org=org, user=current_user, role=OrgRole.owner)
    db.add_all([org, membership])
    await db.commit()
    await db.refresh(org)
    return OrganizationOut.model_validate(org, from_attributes=True)


@router.get("/current/membership", response_model=MembershipOut)
async def current_membership(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_org),
) -> MembershipOut:
    res = await db.execute(
        select(OrgMembership).where(OrgMembership.org_id == current_org.id, OrgMembership.user_id == current_user.id)
    )
    m = res.scalar_one()
    return MembershipOut(
        org_id=m.org_id,
        user_id=m.user_id,
        role=m.role.value,
        created_at=m.created_at,
    )


@router.post("/{org_id}/invites", response_model=InviteCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    org_id: str,
    payload: InviteCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InviteCreatedResponse:
    # Enforce org scope + membership using header or path org_id:
    # For MVP, we accept org_id in path and check membership directly.
    try:
        from uuid import UUID

        parsed_org_id = UUID(org_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid org_id")

    mem = await db.execute(
        select(OrgMembership).where(OrgMembership.org_id == parsed_org_id, OrgMembership.user_id == current_user.id)
    )
    membership = mem.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    if membership.role != OrgRole.owner:
        raise HTTPException(status_code=403, detail="Only owners can invite members")

    role = OrgRole(payload.role)
    token = generate_invite_token()
    expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=payload.expires_in_hours)
    invite = OrgInvite(
        org_id=parsed_org_id,
        email=str(payload.email).lower(),
        role=role,
        token_hash=hash_token(token),
        status=InviteStatus.pending,
        expires_at=expires_at,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    return InviteCreatedResponse(
        invite_id=invite.id,
        email=payload.email,
        role=invite.role.value,
        expires_at=invite.expires_at,
        invite_token=token,
    )


@router.post("/invites/accept", status_code=status.HTTP_204_NO_CONTENT)
async def accept_invite(
    payload: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    token_hash = hash_token(payload.token)
    res = await db.execute(select(OrgInvite).where(OrgInvite.token_hash == token_hash))
    invite = res.scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")

    now = datetime.now(tz=timezone.utc)
    if invite.status != InviteStatus.pending:
        raise HTTPException(status_code=400, detail=f"Invite is not pending ({invite.status.value})")
    if invite.expires_at <= now:
        invite.status = InviteStatus.expired
        await db.commit()
        raise HTTPException(status_code=400, detail="Invite expired")

    # Ensure email matches (basic safety).
    if current_user.email.lower() != invite.email.lower():
        raise HTTPException(status_code=403, detail="Invite email does not match current user")

    # Create membership if not exists.
    mem = await db.execute(
        select(OrgMembership).where(OrgMembership.org_id == invite.org_id, OrgMembership.user_id == current_user.id)
    )
    if mem.scalar_one_or_none() is None:
        db.add(OrgMembership(org_id=invite.org_id, user_id=current_user.id, role=invite.role))

    invite.status = InviteStatus.accepted
    invite.accepted_at = now
    await db.commit()

