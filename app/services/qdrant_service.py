import io

from fastapi.params import Depends
from qdrant_client import QdrantClient
from qdrant_client.http import models
from PIL import Image

from app.schemas.embedding_schema import ItemUpsertRequest
from app.services.embedding_service import get_embedding_service


class QdrantService:
    def __init__(self, embedding_service, host="localhost", port=6333):
        self.embedding_service = embedding_service
        self.client = QdrantClient(host=host, port=port)
        #self.client: AsyncQdrantClient = AsyncQdrantClient(host=host, port=port)
        self.collection_name = "billage_items"

    async def upsert_item(self, data: ItemUpsertRequest, image_data: bytes):
        try:
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            bingsu_vec, dino_vec = self.embedding_service.encode_image(image)

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
            self.client.upsert(
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
        except Exception as e:
            print(f"VectorDB 데이터 저장 실패. Post ID: {data.post_id}")
            return {"status": "fail", "reason": str(e)}

    async def delete_item(self, post_id: int):
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[post_id]
                )
            )
            print(f"VectorDB 데이터 삭제 완료. Post ID: {post_id}")
            return {"status": "deleted", "post_id": post_id}
        except Exception as e:
            print(f"VectorDB 데이터 삭제 실패. Post Id: {post_id}")
            return {"status": "fail", "reason": str(e)}

    async def search_similar_price(self, image_data: bytes):
        # 이미지 벡터화
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        _, image_vec = self.embedding_service.encode_image(image)

        # 유사도 검색.
        try:
            search_result = self.client.query_points(
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
            return {"status": "search_failed", "reason": str(e)}

# 서비스 객체 (전역변수)
_qdrant_service = None

def get_qdrant_service(
    embed_service = Depends(get_embedding_service)
):
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService(embedding_service=embed_service)
    return _qdrant_service