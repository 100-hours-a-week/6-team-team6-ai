from pydantic import BaseModel

# 게시글 기반
class RecommendByItemRequest(BaseModel):
    post_id: int

# OLAP 기반
class RecommendByNeedsRequest(BaseModel):
    user_id: int