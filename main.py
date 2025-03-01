from fastapi import FastAPI, Form, HTTPException
from pydantic import EmailStr
from email_validator import validate_email, EmailNotValidError
from config import users_collection, test_collection
from utils import *

app = FastAPI()

def get_user_collection(testing: bool):
    return test_collection if testing else users_collection

@app.post("/register")
async def register_user(email: EmailStr = Form(...), username: str = Form(...), password: str = Form(...), testing: bool = False):
    collection = get_user_collection(testing)
    try:
        validate_email(email)
    except EmailNotValidError:
        raise HTTPException(status_code=400, detail="Invalid email format")

    if collection.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Username already taken")

    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")
    hashed_password = hash_password(password)

    token = generate_unique_token()

    user = {
        "email": email,
        "username": username,
        "password": hashed_password,
        "verified": False,
        "token": token
    }
    collection.insert_one(user)
    
    if not testing:
        await send_verification_email(email, token)

    return {"message": "User registered successfully! Please check your email to verify your account."}
    
@app.post("/login")
def login_user(username: str = Form(...), password: str = Form(...), testing: bool = False):
    collection = get_user_collection(testing)
    user = collection.find_one({"username": username})
    
    if not user:
        print("User not found in DB!")
        raise HTTPException(status_code=400, detail="Invalid username or password")

    if not user.get("verified", True):
        raise HTTPException(status_code=400, detail="Email not verified. Please check your inbox.")

    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    return {"message": "Login successful!"}

@app.get("/verify/{token}")
def verify_email(token: str, testing: bool = False):
    collection = get_user_collection(testing)
    user = collection.find_one({"token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    collection.update_one({"token": token}, {"$set": {"verified": True}, "$unset": {"token": ""}})

    return {"message": "Email verified successfully! You can now log in."}

@app.get("/")
def home():
    return {"message": "FastAPI MongoDB Backend is Running!"}
