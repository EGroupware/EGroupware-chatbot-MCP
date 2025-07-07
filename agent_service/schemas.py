from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None
    pwd: str | None = None

class EnvironmentConfig(BaseModel):
    egroupware_url: str
    ai_provider: str
    ai_api_key: str
    ionos_base_url: Optional[str] = None
