from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

import os

load_dotenv()

mode = os.getenv("QDRANT_MODE")
#client = QdrantClient(host="localhost", port=6333)

def qdrant_setting():
    client = QdrantClient(host="localhost", port=6333)

    # 중복 테스트
    collection_name = "billage_items"
    if not client.collection_exists(collection_name=collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dino_vec": models.VectorParams(
                    size=1024,
                    distance=models.Distance.COSINE
                ),
                "bingsu_vec": models.VectorParams(
                    size=768,
                    distance=models.Distance.COSINE
                ),
            }
        )
        print(f"'{collection_name}' 컬렉션 생성")
    else:
        print(f"'{collection_name}' 컬렉션 존재")

