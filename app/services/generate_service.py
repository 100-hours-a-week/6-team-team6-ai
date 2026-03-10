import asyncio
import base64
import io
import json
import os
import re

import httpx
from fastapi import HTTPException, UploadFile, Depends
from PIL import Image

from app.prompts.generate_prompt import GENERATE_POST_PROMPT
from app.services.qdrant_service import get_qdrant_service

# 추가: response에서 json 추출
def extract_json(text: str):
    match = re.search(r'```(?:json)?\s*([\{\[].*?[\}\]])\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    return text


class GenerateService:
    def __init__(self, qdrant_service):
        self.qdrant_service = qdrant_service
    async def generate_post(self, images: list[UploadFile]):
        # 이미지 전처리
        task = [self.preprocess_image(image, index == 0) for index, image in enumerate(images)]
        preprocess_images = await asyncio.gather(*task)
        # 내용 생성용 이미지 (Base64)
        base64_images = [res["base64"] for res in preprocess_images]
        # 벡터화(시세산정)용 이미지 (Image)
        thumbnail_image_obj = preprocess_images[0]["image_obj"]

        # Qwen 호출 - 시세 검색 병렬 처리
        vlm_task = asyncio.create_task(self.call_qwen_vlm(base64_images))
        price_task = asyncio.create_task(self.qdrant_service.search_similar_price(thumbnail_image_obj))

        vlm_result, similar_prices = await asyncio.gather(vlm_task, price_task)

        # 시세 산정
        recommend_price = int(sum(similar_prices) / len(similar_prices)) if similar_prices else 0
        print(f"recommend price: {recommend_price}")

        try:
            cleaned_json = extract_json(vlm_result)
            response_data = json.loads(cleaned_json)
            response_data["price"] = recommend_price
            return response_data
        except json.JSONDecodeError:
            # 실패 -> JSON 파싱 에러
            raise Exception(f"JSON 파싱 실패. 원본 response: {vlm_result}")

    async def preprocess_image(self, file: UploadFile, is_thumbnail: bool = False):
        # 디코딩
        image_data = await file.read()
        # RGB 변환: png error 방지..
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        # 리사이징 : 테스트 기반 640x640
        image.thumbnail((640, 640))

        # 바이너리 인코딩
        image_buffer = io.BytesIO()
        image.save(image_buffer, format="WEBP", quality=75)
        # Base64 변환
        resized_binary = image_buffer.getvalue()
        base64_image = base64.b64encode(resized_binary).decode("UTF-8")

        return {
            "base64": base64_image,
            "image_obj": image if is_thumbnail else None
        }

    async def call_qwen_vlm(self, base64_image: list[str]):
        # 페이로드 메세지 구성
        user_prompt = [{"type": "text", "text": "이미지 분석 후 물품을 상세히 설명하는 대여 게시글을 작성하세요."}]
        for b64img in base64_image:
            user_prompt.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64img}"},
                }
            )

        # 페이로드: 서버리스 버전(vLLM 내장 핸들러용: input 추가)
        payload = {
            "input": {
                "model": "Qwen/Qwen2.5-VL-7B-Instruct",
                "messages": [
                    {"role": "system", "content": GENERATE_POST_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 512,
                "temperature": 0.4,
            }
        }

        # URL: runsync로 동기처리.
        target_url = f"https://api.runpod.ai/v2/{os.getenv('QWEN_ENDPOINT_ID')}/runsync"

        # Qwen 호출
        # url 변경, 임의 식별 키 -> 런팟 API 유저 고유 키, 타임아웃 시간 늘리기
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    target_url,
                    headers={"Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}"},
                    json=payload,
                    timeout=120,
                )

                response.raise_for_status()
                result = response.json()
                print(result)

                if result.get("status") != "COMPLETED":
                    raise Exception(f"런팟 작업 실패: {result.get('error')}")

                content_text = result.get("output")
                return content_text

            except httpx.HTTPStatusError as e:
                if e.response.content:
                    error_detail = e.response.json()
                else:
                    error_detail = "런팟 서버 오류"
                raise HTTPException(
                    status_code=e.response.status_code, detail=error_detail
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"알 수 없는 오류: {str(e)}"
                )

def get_generate_service(qdrant_service = Depends(get_qdrant_service)):
    return GenerateService(qdrant_service=qdrant_service)