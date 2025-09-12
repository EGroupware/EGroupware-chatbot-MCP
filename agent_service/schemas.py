from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str
    password: Optional[str] = None
    egw_url: str
    ai_key: str
    provider_type: str
    base_url: Optional[str] = None

class LoginRequest(BaseModel):
    egw_url: str
    ai_key: str
    provider_type: str  # Type of AI provider (openai, ionos, github, etc.)
    base_url: Optional[str] = None  # Base URL for the API (if needed)
    username: str
    password: str