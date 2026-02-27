from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

import os

load_dotenv()

def qdrant_setting():
    #client = QdrantClient(host=os.getenv("QDRANT_HOST"), port=6333)
    client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    print(f"Qdrant 연결 완료. url: {os.getenv('QDRANT_URL')}")

    # items 컬렉션
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

