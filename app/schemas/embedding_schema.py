from pydantic import BaseModel
from enum import Enum


class PriceUnit(str, Enum):
    HOUR = "HOUR"
    DAY = "DAY"

# 벡터DB 저장
# 요청
class ItemCreateRequest(BaseModel):
    user_id: int
    group_id: int
    post_id: int
    title: str
    price: int
    price_unit: PriceUnit
    # 이미지는 따로 받는걸로...
