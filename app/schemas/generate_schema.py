from typing import List

from fastapi import File, UploadFile
from pydantic import BaseModel

# MVP : 게시글 제목/내용 생성
# 응답
class GenerateResponse(BaseModel):
    title: str
    content: str
    isRentable: bool
    price: int
