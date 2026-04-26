from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class CostsSummaryOut(BaseModel):
    from_ts: datetime
    to_ts: datetime
    currency: str = "USD"
    cloud_amount: Decimal
    ai_amount: Decimal
    total_amount: Decimal


GroupBy = Literal["provider", "service", "team", "feature", "model", "account"]


class BreakdownRow(BaseModel):
    scope: Literal["cloud", "ai"]
    group_by: GroupBy
    key: str
    amount: Decimal
    currency: str = "USD"


class CostsBreakdownOut(BaseModel):
    from_ts: datetime
    to_ts: datetime
    group_by: GroupBy
    rows: list[BreakdownRow]

