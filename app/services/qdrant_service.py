import io
import os
import boto3
import numpy as np
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from fastapi.params import Depends
from mpmath import scorergi
from qdrant_client import QdrantClient
from qdrant_client.http import models
from PIL import Image

from app.schemas.embedding_schema import ItemUpsertRequest, NeedsUpsertRequest
from app.schemas.recommend_schema import RecommendByItemRequest, RecommendByNeedsRequest
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
                s3_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
                image_data = s3_response["Body"].read()
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "NoSuchKey":
                    print(f"S3에 해당 이미지가 존재하지 않습니다. file key: {file_key}")
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
                    "message": f"Qdrant 서버 오류: {str(e)}"
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

    async def search_similar_price(self, image: Image.Image):
        # 이미지 벡터화
        #image = Image.open(io.BytesIO(image_data)).convert("RGB")
        image_vec = self.embedding_service.encode_image(image)

        # 유사 물품 가격 찾기 (k=5): 그룹 구별 없는 전체 포스트 기준.
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

            prices = []
            for hit in search_result.points:
                if hit.payload and hit.payload.get("price") is not None:
                    try:
                        print(f"similar item: {hit.payload}")
                        prices.append(int(hit.payload.get("price")))
                    except (ValueError, TypeError):
                        continue
                else:
                    print("유사 물건 없음.")
            return prices
        except Exception as e:
            print(f"Qdrant 서치 중 에러: {str(e)}")
            return []

    async def recommend_by_item(self, data: RecommendByItemRequest):
        try:
            target_point = self.qdrant_client.retrieve(
                collection_name=self.collection_name,
                ids=[data.post_id],
                with_payload=True
            )
            if not target_point:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "status": "retrieve failed",
                        "message": f"요청 게시글 데이터를 찾을 수 없습니다. (post id:{data.post_id})"
                    }
                )
            current_user = target_point[0].payload.get("user_id")
            current_group = target_point[0].payload.get("group_id")
            search_result = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    models.Prefetch(query=data.post_id, using="dino_vec", score_threshold=0.7, limit=10),
                    models.Prefetch(query=data.post_id, using="bingsu_vec", score_threshold=0.7, limit=10)
                ],
                # RRF
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                query_filter=models.Filter(
                    must=[models.FieldCondition(key="group_id", match=models.MatchValue(value=current_group))],
                    must_not=[models.FieldCondition(key="user_id", match=models.MatchValue(value=current_user))]
                ),
                limit=8
            )
            recommendations = []
            for hit in search_result.points:
                print(hit)
                recommendations.append(hit.id)

            print(f"추천 게시글: {recommendations}")
            return {"recommendations": recommendations}

        except HTTPException:
            raise
        except Exception as e:
            print(f"error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "status": "recommend fail",
                    "message": f"error. {str(e)}"
                }
            )

    async def upsert_needs(self, data: NeedsUpsertRequest):
        if not data.recent_logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"status": "fail", "message": "recent logs not found"}
            )

        # 분기
        click_image_list = []
        click_text_list = []
        search_list = []
        try:
            for log in data.recent_logs:
                if log.type == "CLICK":
                    target_post_id = int(log.content)
                    target_point = self.qdrant_client.retrieve(
                        collection_name=self.collection_name,
                        ids = [target_post_id],
                        with_vectors=True
                    )
                    click_image_list.append(target_point[0].vector["dino_vec"])
                    click_text_list.append(target_point[0].vector["bingsu_vec"])
                elif log.type == "SEARCH":
                    target_vector = self.embedding_service.encode_text(log.content)
                    search_list.append(np.array(target_vector) * 3)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail={ "status": "fail", "message": f"action error. action: {log.type}" }
                    )
            # 가중치 계산 + 저장
            image_vec = np.mean(click_image_list, axis=0) if click_image_list else None
            title_vec = np.sum(click_text_list, axis=0) if click_text_list else 0
            keyword_vec = np.sum(search_list, axis=0)if search_list else 0

            denominator = len(click_text_list) + len(search_list) * 3
            text_vec = ((title_vec + keyword_vec) / denominator).tolist()

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={ "status": "fail", "message": f"error. {str(e)}" }
            )
        try:
            self.qdrant_client.upsert(
                collection_name="billage_needs",
                points=[models.PointStruct(
                    id=data.user_id,
                    vector={
                        "dino_vec": image_vec,
                        "bingsu_vec": text_vec
                    },
                    payload={
                        "user_id": data.user_id,
                        "group_id": data.group_id
                    }
                )]
            )
            print(f"VectorDB 데이터 저장 완료. User ID: {data.user_id}")
            return {"status": "update", "user_id": data.user_id}
        except Exception as e:
            print(f"VectorDB 데이터 저장 실패. User ID: {data.user_id} \n reason: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"status": "fail", "message": f"Qdrant 서버 오류: {str(e)}"}
            )

    async def recommend_by_needs(self, data: RecommendByNeedsRequest):
        # 타겟 포인트
        target_point = self.qdrant_client.retrieve(
            collection_name="billage_needs",
            ids=[data.user_id],
            with_vectors=True,
            with_payload=True
        )
        if not target_point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "retrieve failed",
                    "message": f"요청 사용자 데이터를 찾을 수 없습니다. (user id:{data.user_id})"
                }
            )

        group_id = target_point[0].payload["group_id"]
        dino_vec = target_point[0].vector["dino_vec"]
        bingsu_vec = target_point[0].vector["bingsu_vec"]

        # 필터 정의
        search_filter = models.Filter(
            must=[models.FieldCondition(key="group_id", match=models.MatchValue(value=group_id))],
            must_not=[models.FieldCondition(key="user_id", match=models.MatchValue(value=data.user_id))],
        )

        # 후보군
        candidate = self.qdrant_client.query(
            collection_name=self.collection_name,
            query_vector = ("bingsu_vec", bingsu_vec),
            query_filter=search_filter,
            score_threshold=0.6,
            with_payload=True,
            with_vectors=True,
            limit=10
        )

        result = []
        for item in candidate:
            bingsu_score = item.score
            # 이미지 벡터 -> 코사인 유사도 계산
            if dino_vec and "dino_vec" in item.vector:
                dino_score = cosine_similarity(dino_vec, item.vector["dino_vec"])
            else:
                dino_score = 0.5
            # weight = 9:1
            total_score =  (bingsu_score * 0.9) + (dino_score * 0.1)
            result.append({ "id": item.id,
                            "score": total_score,
                            "payload": item.payload })

        result.sort(key=lambda x: x["score"], reverse=True)
        result_limit = 5
        if len(result) < 5:
            result_limit = len(result)
        return result[:result_limit]

def cosine_similarity(a, b):
    # numpy 배열로 변환 : numpy 수식 쓸거라.
    a = np.array(a)
    b = np.array(b)

    # dot product
    dot_product = np.dot(a, b)
    # normalize
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)

# 서비스 객체 (전역변수)
_qdrant_service = None

def get_qdrant_service(
    embed_service = Depends(get_embedding_service)
):
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService(embedding_service=embed_service)
    return _qdrant_service