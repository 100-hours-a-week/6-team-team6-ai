import io
import os
import base64
import boto3
import httpx
from botocore.exceptions import ClientError
from fastapi import HTTPException

from PIL import Image

from app.schemas.validate_schema import ValidateRequest
from app.prompts.validate_prompt import VALIDATE_PROMPT

class ValidateService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120)
        # s3 접근 설정
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY'),
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name = os.getenv('AWS_REGION_NAME')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
    async def validate_post(self, data: ValidateRequest):
        # s3
        try:
            file_key = data.image
            s3_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            image_data = s3_response['Body'].read()
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                print(f"S3에 해당 이미지가 존재하지 않습니다. file key: {file_key}")
                raise HTTPException(status_code=404,
                                    detail={"status": "fail",
                                            "message": f"파일 키를 찾을 수 없습니다. file key: {file_key}"})
            raise HTTPException(status_code=500,
                                detail={ "stats": "fail",
                                         "message": f"s3 통신 오류 발생: {str(e)}" })
        # resize
        image = Image.open(io.BytesIO(image_data)).convert('RGB')
        image = image.resize((448, 448))
        # binary
        image_buffer = io.BytesIO()
        image.save(image_buffer, format="WEBP", quality=75)
        # Base64
        resized_image = image_buffer.getvalue()
        base64_image = base64.b64encode(resized_image).decode("utf-8")

        result = await self.call_llama(base64_image, data.title, data.content)
        return result

    async def call_llama(self, base64_image: str, title: str, content: str):
        user_input = f"Title: {title} / Content: {content}"
        user_prompt = [{"type": "image_url", "image_url": {"url": f"data:image/webp;base64,{base64_image}"}},
                       {"type": "text", "text": VALIDATE_PROMPT + f"\nUser Input: {user_input}"}]
        payload = {
            "input": {
                "model": "resfebel/billage-guard-v3-4bit",
                "messages": [
                    { "role": "user", "content": user_prompt}
                ],
                "max_tokens": 20,
                "temperature": 0
            }
        }

        # call llama
        target_url = f"https://api.runpod.ai/v2/{os.getenv('LLAMA_ENDPOINT_ID')}/runsync"
        try:
            response = await self.client.post(
                target_url,
                headers={"Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}"},
                json=payload,
                timeout=120
            )

            response.raise_for_status()
            full_result = response.json()
            print(full_result)

            if full_result.get("status") != "COMPLETED":
                raise Exception(f"런팟 작업 실패: {full_result.get('error')}")

            result = full_result.get("output")
            return result

        except httpx.HTTPStatusError as e:
            if e.response.content:
                error_detail = e.response.json()
            else: error_detail = "런팟 서버 오류"
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
        except Exception as e:
            raise HTTPException(status_code=500, detail={
                "status": "validate fail",
                "message": f"알 수 없는 오류 : {str(e)}"
            })

def get_validate_service():
    return ValidateService()
