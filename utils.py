import bcrypt
import secrets
import string
import re
from fastapi_mail import FastMail, MessageSchema
from config import *

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


async def send_verification_email(email: str, token: str):
    verification_link = f"http://127.0.0.1:8000/verify/{token}"
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