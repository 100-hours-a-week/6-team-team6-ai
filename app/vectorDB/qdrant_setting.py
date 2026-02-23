from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

import os

load_dotenv()

mode = os.getenv("QDRANT_MODE")
client = QdrantClient(host="localhost", port=6333)

if mode == "local":
    client = QdrantClient(host="localhost", port=6333)

# 중복 테스트
COLLECTION_NAME = "billage_items"
if not client.collection_exists(collection_name=COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dino": models.VectorParams(
                size=1024,
                distance=models.Distance.COSINE
            ),
            "bingsu": models.VectorParams(
                size=768,
                distance=models.Distance.COSINE
            ),
        }
    )
    print(f"'{COLLECTION_NAME}' 컬렉션 생성")
else:
    print(f"'{COLLECTION_NAME}' 컬렉션 존재")