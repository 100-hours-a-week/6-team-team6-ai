import os
from typing import List

import httpx
from fastapi import APIRouter, File, UploadFile, status

from app.schemas import qwen_schema
from app.services.service_ai import QwenServiceAI

router = APIRouter(
    prefix="/ai",
    tags=["ai"],
)

service_qwen = QwenServiceAI()

# Qwen 헬스체크
@router.get("/qwen/health")
async def health():
    headers = {
        "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}",
        #"Content-Type": "application/json"
    }
    endpoint_id = os.getenv('QWEN_ENDPOINT_ID')
    async with httpx.AsyncClient() as client:
        try:
            target_url = f"https://api.runpod.ai/v2/{endpoint_id}/health"
            resp = await client.get(target_url, headers=headers, timeout=10.0)

            return {
                "status": "ok" if resp.status_code == 200 else "error",
                "message": "Qwen 연결 완료"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"런팟 엔드포인트 접근 실패: {str(e)}"
            }


# Qwen 게시글 생성 api
@router.post("/generate", response_model=qwen_schema.GenerateResponse,
             status_code=status.HTTP_201_CREATED, summary="게시글 생성")
async def generate_post(images: List[UploadFile] = File(...)):
    return await service_qwen.generate_post(images)


