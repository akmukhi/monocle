from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org
from app.db.session import get_db
from app.models.organization import Organization
from app.schemas.ai import AIGroupBy, AIUsageOut, AIUsageRow
from app.services.ai_queries import ai_usage

router = APIRouter(prefix="/ai")


def _default_range() -> tuple[datetime, datetime]:
    to_ts = datetime.now(tz=timezone.utc)
    from_ts = to_ts - timedelta(days=30)
    return from_ts, to_ts


@router.get("/usage", response_model=AIUsageOut)
async def usage(
    group_by: AIGroupBy = Query(default="model"),
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> AIUsageOut:
    if from_ts is None or to_ts is None:
        df, dt = _default_range()
        from_ts = from_ts or df
        to_ts = to_ts or dt

    rows = await ai_usage(db, org_id=org.id, from_ts=from_ts, to_ts=to_ts, group_by=group_by)
    out_rows = [
        AIUsageRow(
            group_by=group_by,
            key=str(k),
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            requests=int(requests),
            amount=amount,
        )
        for (k, input_tokens, output_tokens, requests, amount) in rows
    ]
    return AIUsageOut(from_ts=from_ts, to_ts=to_ts, group_by=group_by, rows=out_rows)

