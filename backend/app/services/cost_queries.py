from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import String, cast, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.costs import AIUsageCost, CloudCost


def _sum_amount(expr):
    # Postgres SUM(Numeric) yields Decimal; coalesce keeps type stable.
    return func.coalesce(func.sum(expr), 0)


def _ensure_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def costs_summary(db: AsyncSession, *, org_id, from_ts: datetime, to_ts: datetime) -> tuple[Decimal, Decimal]:
    from_ts = _ensure_tz(from_ts)
    to_ts = _ensure_tz(to_ts)

    cloud_q = select(_sum_amount(CloudCost.amount)).where(
        CloudCost.org_id == org_id,
        CloudCost.usage_start >= from_ts,
        CloudCost.usage_start < to_ts,
    )
    ai_q = select(_sum_amount(AIUsageCost.amount)).where(
        AIUsageCost.org_id == org_id,
        AIUsageCost.usage_start >= from_ts,
        AIUsageCost.usage_start < to_ts,
    )

    cloud = (await db.execute(cloud_q)).scalar_one()
    ai = (await db.execute(ai_q)).scalar_one()
    return cloud, ai


GroupBy = Literal["provider", "service", "team", "feature", "model", "account"]


async def costs_breakdown(
    db: AsyncSession,
    *,
    org_id,
    from_ts: datetime,
    to_ts: datetime,
    group_by: GroupBy,
) -> list[tuple[str, str, Decimal]]:
    """
    Returns list of (scope, key, amount) where scope in {"cloud","ai"}.
    """
    from_ts = _ensure_tz(from_ts)
    to_ts = _ensure_tz(to_ts)

    rows: list[tuple[str, str, Decimal]] = []

    # CLOUD
    if group_by == "provider":
        key_expr = cast(CloudCost.provider, String)
    elif group_by == "service":
        key_expr = func.coalesce(CloudCost.service_key, "unknown")
    elif group_by == "account":
        key_expr = func.coalesce(CloudCost.account_or_project, "unknown")
    elif group_by in ("team", "feature"):
        key_expr = func.coalesce(CloudCost.tags[group_by].astext, "unattributed")
    elif group_by in ("model",):
        key_expr = literal("n/a")  # not meaningful for cloud
    else:
        raise HTTPException(status_code=400, detail="Unsupported group_by")

    if group_by != "model":
        cloud_amt = _sum_amount(CloudCost.amount).label("amt")
        cloud_q = (
            select(key_expr.label("k"), cloud_amt)
            .where(
                CloudCost.org_id == org_id,
                CloudCost.usage_start >= from_ts,
                CloudCost.usage_start < to_ts,
            )
            .group_by("k")
            .order_by(cloud_amt.desc())
        )
        res = await db.execute(cloud_q)
        rows.extend([("cloud", str(k), amt) for (k, amt) in res.all()])

    # AI
    if group_by == "provider":
        ai_key_expr = cast(AIUsageCost.provider, String)
    elif group_by == "model":
        ai_key_expr = AIUsageCost.model
    elif group_by == "feature":
        ai_key_expr = func.coalesce(AIUsageCost.feature_key, AIUsageCost.tags["feature"].astext, "unattributed")
    elif group_by == "team":
        ai_key_expr = func.coalesce(AIUsageCost.tags["team"].astext, "unattributed")
    elif group_by in ("service", "account"):
        # Not yet represented on AI rows; use tags if present.
        tag_key = "service" if group_by == "service" else "account"
        ai_key_expr = func.coalesce(AIUsageCost.tags[tag_key].astext, "unattributed")
    else:
        raise HTTPException(status_code=400, detail="Unsupported group_by")

    ai_amt = _sum_amount(AIUsageCost.amount).label("amt")
    ai_q = (
        select(ai_key_expr.label("k"), ai_amt)
        .where(
            AIUsageCost.org_id == org_id,
            AIUsageCost.usage_start >= from_ts,
            AIUsageCost.usage_start < to_ts,
        )
        .group_by("k")
        .order_by(ai_amt.desc())
    )
    ai_res = await db.execute(ai_q)
    rows.extend([("ai", str(k), amt) for (k, amt) in ai_res.all()])

    return rows

