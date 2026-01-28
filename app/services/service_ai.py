import io
import os
import base64
import httpx
import json

from fastapi import UploadFile, HTTPException

from app.prompts.generate_prompt import GENERATE_POST_PROMPT
from PIL import Image

import asyncio


class QwenServiceAI:
    async def generate_post(self, images: list[UploadFile]):
        image_list = [self.preprocess_image(target) for target in images]
        base64_image = await asyncio.gather(*image_list)

        # 페이로드 메세지 구성
        user_prompt = [{"type": "text",
                        "text": "이미지 분석 후 대여 게시글을 작성하세요."}]
        for b64img in base64_image:
            user_prompt.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64img}"}
            })

        # 페이로드
        payload = {
            "model": "Qwen/Qwen2.5-VL-7B-Instruct",
            "messages": [
                {"role": "system", "content": GENERATE_POST_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 1000
        }

        # Qwen 호출
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{os.getenv('QWEN_URL')}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {os.getenv('RUNPOD_QWEN_KEY')}"},
                    json=payload,
                    timeout=60
                )

                response.raise_for_status()
                result = response.json()

                # content만
                content_text = result["choices"][0]["message"]["content"]
                return json.loads(content_text)

            except httpx.HTTPStatusError as e:
                error_detail = e.response.json() if e.response.content else "런팟 서버 오류"
                raise HTTPException(status_code=e.response.status_code, detail=error_detail)

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"알 수 없는 오류: {str(e)}")


    async def preprocess_image(self, file: UploadFile) -> str:
        # 디코딩
        image_data = await file.read()
        # 리사이징 : 테스트 기반 720x720 (640까지 가도 괜찮을 것)
        image = Image.open(io.BytesIO(image_data))
        image.thumbnail((720, 720))
        # 바이너리 인코딩
        image_buffer = io.BytesIO()
        image.save(image_buffer, format='JPEG', quality=85)  # 포맷,퀄리티는 변동할 수 있음...
        # Base64 변환
        resized_binary = image_buffer.getvalue()
        base64_image = base64.b64encode(resized_binary).decode('UTF-8')

        return base64_image

