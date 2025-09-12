import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import requests

from .schemas import TokenData, LoginRequest

# In-memory storage to replace database
user_store: Dict[str, Dict] = {}

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Create a JWT token with an expiration time
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Verify EGroupware credentials by making a request to the addressbook endpoint
def verify_egroupware_credentials(url: str, username: str, password: str) -> bool:
    # Handle both base EGroupware URL and GroupDAV URL formats
    if '/groupdav.php' in url:
        # Extract base URL from GroupDAV URL
        base_url = url.split('/groupdav.php')[0]
    else:
        base_url = url.rstrip('/')

    test_url = f"{base_url}/addressbook/"
    try:
        response = requests.get(test_url, auth=(username, password), params={'limit': 1}, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False


def verify_and_save_credentials(username: str, password: str, egw_url: str) -> bool:
    # First verify with EGroupware
    if not verify_egroupware_credentials(egw_url, username, password):
        return False

    # Store user credentials in memory
    user_store[username] = {
        "username": username,
        "password": password,
        "egw_url": egw_url,
        "updated_at": datetime.utcnow()
    }
    return True


def verify_stored_credentials(username: str, password: str) -> Optional[Dict]:
    user = user_store.get(username)
    if not user or user["password"] != password:
        return None
    return user


# Authenticate user credentials and return a JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
    )
    try:
        # Decode the entire payload
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check if all required keys exist
        username: str = payload.get("sub")
        password: str = payload.get("pwd")
        egw_url: str = payload.get("egw_url")
        ai_key: str = payload.get("ai_key")
        provider_type: str = payload.get("provider_type")
        base_url: Optional[str] = payload.get("base_url")

        # Validate that we have the required fields
        if username is None or password is None or egw_url is None or ai_key is None or provider_type is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Return the user data
    return TokenData(
        username=username,
        password=password,
        egw_url=egw_url,
        ai_key=ai_key,
        provider_type=provider_type,
        base_url=base_url
    )