import base64
import os
import sys
import runpod
import httpx
import asyncio
import time

"""
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from app.services.service_ai import QwenServiceAI

# UploadFile 대체용
class MockUploadFile:
    def __init__(self, base64_data):
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]
        self.content = base64.b64decode(base64_data)
    async def read(self):
        return self.content

service = QwenServiceAI()

# 핸들러
async def handler(job) :
    job_input = job.get("input", {})

    base64_images = job_input.get("images", [])
    if not base64_images:
        return { "error" : "이미지 데이터가 없습니다." }

    try:
        mock_files = [MockUploadFile(image) for image in base64_images]

        result = await service.generate_post(images = mock_files)
        return result

    except Exception as e:
        return { "error": f"서버 내 오류가 발생했습니다 : {e}" }
"""

# 엔진 준비 확인
async def wait_for_vllm():
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get("http://127.0.0.1:8000/v1/models", timeout=1.0)
                if response.status_code == 200:
                    print("vLLM 엔진이 성공적으로 준비되었습니다!")
                    break
            except Exception:
                print("vLLM 엔진 로딩 중... (8000번 포트 대기 중)")
                await asyncio.sleep(5)  # 5초마다 재시도


# vLLM 리퀘스트 타입 이슈: 새로운 수동 핸들러 방식 시도중. . .
async def handler(job):
    job_input = job.get("input", {})

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://127.0.0.1:8000/v1/chat/completions",
                json = job_input,
                timeout = 120
            )
            return response.json()

        except Exception as e:
            return {"error": f"vLLM Proxy 에러: {e}"}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})


