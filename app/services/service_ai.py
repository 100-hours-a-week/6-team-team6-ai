import asyncio
import base64
import io
import json
import os
import re

import httpx
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.prompts.generate_prompt import GENERATE_POST_PROMPT


# 추가: response에서 json 추출
def extract_json(text: str):
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        return match.group(1)
    return text

class QwenServiceAI:
    async def generate_post(self, images: list[UploadFile]):
        image_list = [self.preprocess_image(target) for target in images]
        base64_image = await asyncio.gather(*image_list)

        # 페이로드 메세지 구성
        user_prompt = [{
            "type": "text",
            "text": "이미지 분석 후 대여 게시글을 작성하세요."
        }]
        for b64img in base64_image:
            user_prompt.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64img}"}
            })

        # 페이로드: 서버리스 버전(vLLM 내장 핸들러용: input 추가)
        payload = {
            "input": {
                "model": "Qwen/Qwen2.5-VL-7B-Instruct",
                "messages": [
                    {"role": "system", "content": GENERATE_POST_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 512,
                "temperature": 0.2
            }
        }

        # URL: 서버리스 버전. runsync로 동기처리.
        target_url = f"https://api.runpod.ai/v2/{os.getenv('QWEN_ENDPOINT_ID')}/runsync"


        # Qwen 호출
        # url 변경, 임의 식별 키 -> 런팟 API 유저 고유 키, 타임아웃 시간 늘리기
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    target_url,
                    headers={"Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}"},
                    json=payload,
                    timeout=120
                )

                response.raise_for_status()
                result = response.json()

                if result.get("status") != "COMPLETED":
                    raise Exception(f"런팟 작업 실패: {result.get('error')}")

                # content만 : 서버리스는 output에서 찾도록 수정.
                choices = result["output"]["choices"]

                if not choices:
                    raise Exception(f"모델 응답 형식이 올바르지 않습니다: {choices}")

                content_text = choices[0]["message"]["content"]
                try:
                    cleaned_json = extract_json(content_text)
                    return json.loads(cleaned_json)
                except json.JSONDecodeError:
                    # 실패 -> JSON 파싱 에러
                    raise Exception(f"JSON 파싱 실패. 원본 response: {content_text}")


            except httpx.HTTPStatusError as e:
                if e.response.content:
                    error_detail = e.response.json()
                else:
                    error_detail = "런팟 서버 오류"
                raise HTTPException(status_code=e.response.status_code,
                                    detail=error_detail)

            except Exception as e:
                raise HTTPException(status_code=500,
                                    detail=f"알 수 없는 오류: {str(e)}")


    async def preprocess_image(self, file: UploadFile) -> str:
        # 디코딩
        image_data = await file.read()
        # 리사이징 : 테스트 기반 640x640
        image = Image.open(io.BytesIO(image_data))
        image.thumbnail((640, 640))
        # 바이너리 인코딩
        image_buffer = io.BytesIO()
        # 포맷,퀄리티는 성능따라 변동될 수 있음.
        image.save(image_buffer, format='JPEG', quality=80)
        # Base64 변환
        resized_binary = image_buffer.getvalue()
        base64_image = base64.b64encode(resized_binary).decode('UTF-8')

        return base64_image

