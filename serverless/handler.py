import base64
import os
import sys
import asyncio
import runpod

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
async def handler_async(job) :
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

def handler(job):
    return asyncio.run(handler_async(job))

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})






