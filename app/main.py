import os
import uvicorn
import httpx
from fastapi import FastAPI
from dotenv import load_dotenv

from app.routers import qwen_router


load_dotenv()
app = FastAPI()

app.include_router(qwen_router.router)

@app.get("/ai/health")
async def health_check():
    return {"status": "healthy"}