import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from .schemas import TokenData

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
EGROUPWARE_BASE_URL = os.getenv("EGROUPWARE_BASE_URL")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Create a JWT token with an expiration time
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Verify EGroupware credentials by making a request to the addressbook endpoint
def verify_egroupware_credentials(username: str, password: str) -> bool:
    if not EGROUPWARE_BASE_URL:
        raise ValueError("EGROUPWARE_BASE_URL is not set.")

    test_url = f"{EGROUPWARE_BASE_URL}/addressbook/"
    try:
        response = requests.get(test_url, auth=(username, password), params={'limit': 1}, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False

# Authenticate user credentials and return a JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        password: Optional[str] = payload.get("pwd")
        if username is None or password is None:
            raise credentials_exception
        return TokenData(username=username, password=password)
    except JWTError:
        raise credentials_exception