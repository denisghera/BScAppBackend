import bcrypt
import secrets
import string
import re
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi_mail import FastMail, MessageSchema
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from config import *

bearer_scheme = HTTPBearer()

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_password.decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

def generate_unique_token() -> str:
    while True:
        token = secrets.token_urlsafe(32)
        if not user_credentials_collection.find_one({"token": token}):
            return token  


async def send_verification_email(email: str, token: str, type: str):
    type_url = ''
    if type == 'user':
        type_url = 'verify'
    elif type == 'tutor':
        type_url = 'verify-tutor'
    verification_link = f"http://127.0.0.1:8000/{type_url}/{token}"
    message = MessageSchema(
        subject="Verify Your Email",
        recipients=[email],
        body=f"Click the link to verify your email: \n\n{verification_link}",
        subtype="plain"
    )

    fm = FastMail(conf)
    await fm.send_message(message)

def extract_error_message(error_text):
    match = re.search(r"(\w*Error):\s*(.*)", error_text)
    return match.group(1) + ": " + match.group(2) if match else "Unknown Error"

def generate_access_code(length = 6):
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(username: str):
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": username, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        if not username or token_type != "access":
            raise JWTError()
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Double-check user exists & is verified:
    user = user_credentials_collection.find_one({"username": username})
    if not user or not user.get("verified", False):
        raise HTTPException(status_code=401, detail="User not found or not verified")
    return username

def verify_tutor_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        if not username or token_type != "access":
            raise JWTError()
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check tutor exists and is verified:
    tutor = tutor_credentials_collection.find_one({"username": username})
    if not tutor or not tutor.get("verified", False) or not tutor.get("approved", False):
        raise HTTPException(status_code=401, detail="Tutor not found or not verified/approved")

    return username