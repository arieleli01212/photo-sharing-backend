from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

class GoogleToken(BaseModel):
    token: str

class User(BaseModel):
    username: str
    email: str
    name: str
    provider: str
    google_id: Optional[str] = None