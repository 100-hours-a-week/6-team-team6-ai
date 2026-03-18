from pydantic import BaseModel
from enum import Enum


class PriceUnit(str, Enum):
    HOUR = "HOUR"
    DAY = "DAY"

# 벡터DB 저장
# 요청
class ItemUpsertRequest(BaseModel):
    user_id: int
    group_id: int
    post_id: int
    title: str
    price: int
    price_unit: PriceUnit
    file_key: str
