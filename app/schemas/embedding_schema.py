from pydantic import BaseModel
from enum import Enum
from typing import List

# items 벡터DB
class PriceUnit(str, Enum):
    HOUR = "HOUR"
    DAY = "DAY"

# 저장 요청
class ItemUpsertRequest(BaseModel):
    user_id: int
    group_id: int
    post_id: int
    title: str
    price: int
    price_unit: PriceUnit
    file_key: str

# needs 벡터DB
class ActionUnit(str, Enum):
    SEARCH = "SEARCH"
    CLICK = "CLICK"

class UserLogs(BaseModel):
    type: ActionUnit
    content: str

class NeedsUpsertRequest(BaseModel):
    user_id: int
    #group_id: int
    recent_logs: List[UserLogs]
