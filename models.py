from pydantic import BaseModel, Field
from typing import Optional

class Todo(BaseModel):
    item: str = Field(..., min_length=2, max_length=100)
