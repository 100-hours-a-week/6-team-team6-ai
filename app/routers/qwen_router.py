import os, httpx

from fastapi import APIRouter, UploadFile, File, status
from app.services.service_ai import QwenServiceAI
from app.schemas import qwen_schema
from typing import List


router = APIRouter(
    prefix="/ai",
    tags=["ai"],
)

service_qwen = QwenServiceAI()

# Qwen 헬스체크
@router.get("/qwen/health")
async def health():
    headers = {
        "Authorization": f"Bearer {os.getenv('RUNPOD_QWEN_KEY')}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient() as client:
        try:
            target_url = f"{os.getenv('QWEN_POD_URL')}/v1/models"
            resp = await client.get(target_url, headers=headers, timeout=10.0)

            if resp.status_code == 200:
                return {
                    "status": "ok",
                    "remote_model": resp.json()["data"][0]["id"],
                    "message": "Qwen 연결 완료.."
                }
        except Exception as e:

            return {"status": "error", "message": f"런팟 연결 실패: {str(e)}"}


# Qwen 게시글 생성 api
@router.post("/generate", response_model=qwen_schema.GenerateResponse,
             status_code=status.HTTP_201_CREATED, summary="게시글 생성")
async def generate_post(images: List[UploadFile] = File(...)):
    return await service_qwen.generate_post(images)


