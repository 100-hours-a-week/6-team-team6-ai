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
    qdrant_setting()
    get_embedding_service()
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
