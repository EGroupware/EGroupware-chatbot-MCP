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
    is_ionos: bool
    ionos_base_url: Optional[str] = None

class LoginRequest(BaseModel):
    egw_url: str
    ai_key: str
    ionos_base_url: Optional[str] = None
    username: str
    password: str
