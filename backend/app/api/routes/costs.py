from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org
from app.db.session import get_db
from app.models.organization import Organization
from app.schemas.costs import CostsBreakdownOut, CostsSummaryOut, BreakdownRow, GroupBy
from app.services.cost_queries import costs_breakdown, costs_summary

router = APIRouter(prefix="/costs")


def _default_range() -> tuple[datetime, datetime]:
    to_ts = datetime.now(tz=timezone.utc)
    from_ts = to_ts - timedelta(days=30)
    return from_ts, to_ts


@router.get("/summary", response_model=CostsSummaryOut)
async def summary(
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> CostsSummaryOut:
    if from_ts is None or to_ts is None:
        df, dt = _default_range()
        from_ts = from_ts or df
        to_ts = to_ts or dt

    cloud_amt, ai_amt = await costs_summary(db, org_id=org.id, from_ts=from_ts, to_ts=to_ts)
    total = cloud_amt + ai_amt
    return CostsSummaryOut(from_ts=from_ts, to_ts=to_ts, cloud_amount=cloud_amt, ai_amount=ai_amt, total_amount=total)


@router.get("/breakdown", response_model=CostsBreakdownOut)
async def breakdown(
    group_by: GroupBy = Query(default="provider"),
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> CostsBreakdownOut:
    if from_ts is None or to_ts is None:
        df, dt = _default_range()
        from_ts = from_ts or df
        to_ts = to_ts or dt

    rows = await costs_breakdown(db, org_id=org.id, from_ts=from_ts, to_ts=to_ts, group_by=group_by)
    out_rows = [BreakdownRow(scope=scope, group_by=group_by, key=key, amount=amt) for (scope, key, amt) in rows]
    return CostsBreakdownOut(from_ts=from_ts, to_ts=to_ts, group_by=group_by, rows=out_rows)

