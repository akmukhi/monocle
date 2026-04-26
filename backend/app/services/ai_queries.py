from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.costs import AIUsageCost


AIGroupBy = Literal["model", "feature", "provider"]


def _ensure_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def ai_usage(
    db: AsyncSession,
    *,
    org_id,
    from_ts: datetime,
    to_ts: datetime,
    group_by: AIGroupBy,
) -> list[tuple[str, int, int, int, object]]:
    from_ts = _ensure_tz(from_ts)
    to_ts = _ensure_tz(to_ts)

    if group_by == "provider":
        key_expr = cast(AIUsageCost.provider, String)
    elif group_by == "model":
        key_expr = AIUsageCost.model
    elif group_by == "feature":
        key_expr = func.coalesce(AIUsageCost.feature_key, AIUsageCost.tags["feature"].astext, "unattributed")
    else:
        raise HTTPException(status_code=400, detail="Unsupported group_by")

    amt = func.coalesce(func.sum(AIUsageCost.amount), 0).label("amount")
    q = (
        select(
            key_expr.label("k"),
            func.coalesce(func.sum(AIUsageCost.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(AIUsageCost.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(AIUsageCost.requests), 0).label("requests"),
            amt,
        )
        .where(
            AIUsageCost.org_id == org_id,
            AIUsageCost.usage_start >= from_ts,
            AIUsageCost.usage_start < to_ts,
        )
        .group_by("k")
        .order_by(amt.desc())
    )
    res = await db.execute(q)
    return list(res.all())

