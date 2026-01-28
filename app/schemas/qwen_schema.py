from pydantic import BaseModel
from typing import List
from fastapi import UploadFile, File


# MVP : 게시글 제목/내용 생성
# 요청

class GenerateRequest(BaseModel):
    images: List[UploadFile]    #필수

    @classmethod
    def as_form(cls, images: List[UploadFile] = File(...)):
        return cls(images=images)

# 응답
class GenerateResponse(BaseModel):
    title: str
    content: str