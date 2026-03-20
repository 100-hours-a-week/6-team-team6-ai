import os
from typing import List

import httpx
from fastapi import APIRouter, File, UploadFile, status, Form, Depends, HTTPException

from app.schemas import generate_schema, embedding_schema, recommend_schema, validate_schema
from app.services.generate_service import GenerateService, get_generate_service
from app.services.qdrant_service import QdrantService, get_qdrant_service
from app.services.validate_service import ValidateService, get_validate_service

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

@router.post("/items/upsert", tags=["Items"], summary="벡터DB items 저장")
async def upsert_item(data: embedding_schema.ItemUpsertRequest,
                      qdrant_service: QdrantService = Depends(get_qdrant_service)):
    return await qdrant_service.upsert_item(data)


@router.delete("/items/{post_id}", tags=["Items"], summary="벡터DB items 삭제")
async def delete_item(post_id: int,
                      qdrant_service: QdrantService = Depends(get_qdrant_service)):
    return await qdrant_service.delete_item(post_id)

@router.post("/items/recommend", tags=["Recommend"], summary="게시글 기반 추천")
async def recommend_item(data: recommend_schema.RecommendByItemRequest,
                         qdrant_service: QdrantService = Depends(get_qdrant_service)):
    return await qdrant_service.recommend_by_item(data)

@router.post("/needs/upsert", tags=["Needs"], summary="벡터DB needs 저장")
async def upsert_needs(data: embedding_schema.NeedsUpsertRequest,
                       qdrant_service: QdrantService = Depends(get_qdrant_service)):
    return await qdrant_service.upsert_needs(data)

@router.post("/needs/recommend", tags=["Recommend"], summary="니즈 기반 추천")
async def recommend_needs(data: recommend_schema.RecommendByNeedsRequest,
                          qdrant_service: QdrantService = Depends(get_qdrant_service)):
    return await qdrant_service.recommend_by_needs(data)
#
# @router.post("/validate", tags=["validate"], summary="게시글 검증")
# async def validate_post(data: validate_schema.ValidateRequest,
#                         validate_service: ValidateService = Depends(get_validate_service)):
#     return await validate_service.validate_post(data)