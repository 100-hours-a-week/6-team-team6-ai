import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.services.embedding_service import get_embedding_service
from app.routers import qwen_router
#from app.routers import test_router
from app.vectorDB.qdrant_setting import qdrant_setting
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Qdrant 설정 확인 중")
    try:
        qdrant_setting()
        print("Qdrant 설정 및 컬렉션 확인 완료")
        get_embedding_service()
        print("임베딩 서비스 로드 완료")
    except Exception as e:
        print(f"Qdrant 설정 실패: {e}")
        raise e
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(qwen_router.router)
#app.include_router(test_router.router)


@app.get("/ai/health")
async def health_check():
    return {"status": "healthy"}


# local test
if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
