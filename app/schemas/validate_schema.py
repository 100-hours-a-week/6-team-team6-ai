from pydantic import BaseModel

class ValidateRequest(BaseModel):
    image: str
    title: str
    content: str