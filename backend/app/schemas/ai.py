from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


AIGroupBy = Literal["model", "feature", "provider"]


class AIUsageRow(BaseModel):
    group_by: AIGroupBy
    key: str
    input_tokens: int
    output_tokens: int
    requests: int
    amount: Decimal
    currency: str = "USD"


class AIUsageOut(BaseModel):
    from_ts: datetime
    to_ts: datetime
    group_by: AIGroupBy
    rows: list[AIUsageRow]

