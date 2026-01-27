from fastapi import FastAPI

app = FastAPI()


@app.get("/ai/health")
async def health_check():
    return {"status": "healthy"}
