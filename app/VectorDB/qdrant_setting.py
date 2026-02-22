from qdrant_client import QdrantClient

USE_LOCAL_MODE = True
if(USE_LOCAL_MODE):
    QdrantClient(path="./qdrant_db")
else:
    QdrantClient(host="localhost", port=6333)