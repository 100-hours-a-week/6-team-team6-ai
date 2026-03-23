from pydantic import BaseModel
from typing import List

class ValidateRequest(BaseModel):
    #image: str
    images: List[str]
    title: str
    content: str