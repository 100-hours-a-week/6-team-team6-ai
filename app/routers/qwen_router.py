import os
from typing import List

import httpx
from fastapi import APIRouter, File, UploadFile, status, Form, Depends, HTTPException
from fastapi.params import Depends

from app.schemas import generate_schema
from app.schemas.embedding_schema import ItemCreateRequest
from app.services.generate_service import GenerateService, get_generate_service
from app.services.qdrant_service import get_qdrant_service, QdrantService

router = APIRouter(
    prefix="/ai"
)


# Qwen 헬스체크
@router.get("/qwen/health")
async def health():
    headers = {
        "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}",
    }
    endpoint_id = os.getenv("QWEN_ENDPOINT_ID")
    async with httpx.AsyncClient() as client:
        try:
            target_url = f"https://api.runpod.ai/v2/{endpoint_id}/health"
            resp = await client.get(target_url, headers=headers, timeout=10.0)

            return {
                "status": "ok" if resp.status_code == 200 else "error",
                "message": "Qwen 연결 완료",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"런팟 엔드포인트 접근 실패: {str(e)}",
            }

# Qwen 게시글 생성 api
@router.post(
    "/generate",
    response_model=generate_schema.GenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="게시글 생성",
)
async def generate_post(images: List[UploadFile] = File(...),
                        generate_service: GenerateService = Depends(get_generate_service)):
    return await generate_service.generate_post(images)

@router.post("/items/upsert", tags=["Items"], summary="벡터DB 저장")
async def create_item(data: str = Form(...),
                      image: UploadFile = File(...),
                      qdrant_service: QdrantService = Depends(get_qdrant_service)):
    try:
        request_data = ItemCreateRequest.model_validate_json(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"JSON 파싱 에러: {e}")

    image_data = await image.read()
    return await qdrant_service.upsert_item(request_data, image_data)


@router.delete("/items/{post_id}", tags=["Items"], summary="벡터DB 삭제")
async def delete_item(post_id: int,
                      qdrant_service: QdrantService = Depends(get_qdrant_service)):
    return await qdrant_service.delete_item(post_id)
