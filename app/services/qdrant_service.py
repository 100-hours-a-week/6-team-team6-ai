import io
import os
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from fastapi.params import Depends
from qdrant_client import QdrantClient
from qdrant_client.http import models
from PIL import Image

from app.schemas.embedding_schema import ItemUpsertRequest
from app.services.embedding_service import get_embedding_service


class QdrantService:
    def __init__(self, embedding_service):
        self.embedding_service = embedding_service
        # VectorDB setting
        self.qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"),
                                          api_key=os.getenv("QDRANT_API_KEY", None))
        self.collection_name = "billage_items"
        # S3 setting
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY'),
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name = os.getenv('AWS_REGION_NAME'),
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME')

    async def upsert_item(self, data: ItemUpsertRequest):
        try:
            # S3
            try:
                file_key = data.file_key
                print(file_key)
                s3_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
                image_data = s3_response["Body"].read()
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "NoSuchKey":
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail={
                            "status": "fail",
                            "message": f"S3에 해당 이미지가 존재하지 않습니다. file key: {file_key}"
                        }
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "status": "fail",
                        "message": f"S3 통신 오류 발생: {str(e)}"
                    }
                )
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            dino_vec = self.embedding_service.encode_image(image)

            post_title = data.title
            bingsu_vec = self.embedding_service.encode_text(post_title)

            # 가격 -> 시간 단위로 보정
            item_price = data.price
            if data.price_unit == "DAY":
                item_price = int(item_price / 24)
            payload = {
                "user_id": data.user_id,
                "group_id": data.group_id,
                "post_id": data.post_id,
                "price": item_price
            }
            # 저장
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=data.post_id,
                        vector={
                            "dino_vec": dino_vec,
                            "bingsu_vec": bingsu_vec
                        },
                        payload=payload
                    )
                ]
            )
            print(f"VectorDB 데이터 저장 완료. Post ID: {data.post_id}")
            return {"status": "success"}
        except HTTPException:
            raise
        except Exception as e:
            print(f"VectorDB 데이터 저장 실패. Post ID: {data.post_id} \n reason: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "status": "fail",
                    "message": "Qdrant 서버 오류: {str(e)}"
                }
            )

    async def delete_item(self, post_id: int):
        try:
            existing_point = self.qdrant_client.retrieve(
                collection_name=self.collection_name,
                ids=[post_id]
            )
            if not existing_point:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "status": "fail",
                        "message": f"VectorDB 데이터 삭제 실패. reason: 삭제할 데이터를 찾을 수 없습니다. (post id: {post_id})"
                    }
                )

            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[post_id])
            )
            print(f"VectorDB 데이터 삭제 완료. Post ID: {post_id}")
            return {"status": "deleted", "post_id": post_id}
        except HTTPException:
            raise
        except Exception as e:
            print(f"VectorDB 데이터 삭제 실패. Post Id: {post_id} \n reason: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "status": "fail",
                    "message": f"VectorDB 데이터 삭제 실패. reason: {str(e)}"}
            )

    async def search_similar_price(self, image_data: bytes):
        # 이미지 벡터화
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        image_vec = self.embedding_service.encode_image(image)

        # 유사도 검색.
        try:
            search_result = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=image_vec,
                using="dino_vec",
                # 조정 가능성 o
                score_threshold=0.7,
                limit=5,
                with_payload=True
            )


            for hit in search_result.points:
                print(f"similar item: {hit.payload}")
            return [hit.payload.get("price") for hit in search_result.points if hit.payload]
        except Exception as e:
            print(f"reason: str(e)")
            return {"status": "search_failed",
                    "reason": str(e)}

# 서비스 객체 (전역변수)
_qdrant_service = None

def get_qdrant_service(
    embed_service = Depends(get_embedding_service)
):
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService(embedding_service=embed_service)
    return _qdrant_service