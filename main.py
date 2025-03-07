from pydantic import ValidationError
from fastapi import FastAPI, HTTPException
from email_validator import validate_email, EmailNotValidError
from config import users_collection, test_collection, daily_puzzle_collection, user_file_collection
from models import *
from utils import *
from datetime import datetime

app = FastAPI()

def get_user_collection(testing: bool):
    return test_collection if testing else users_collection

def get_daily_puzzle_collection(testing: bool):
    return test_collection if testing else daily_puzzle_collection

def get_user_file_collection(testing: bool):
    return test_collection if testing else user_file_collection

@app.post("/register")
async def register_user(user: UserRegister, testing: bool = False):
    collection = get_user_collection(testing)
    try:
        validate_email(user.email)
    except (EmailNotValidError, ValidationError):
        raise HTTPException(status_code=400, detail="Invalid email format")

    if collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already taken")

    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")
    hashed_password = hash_password(user.password)

    token = generate_unique_token()

    dbUser = {
        "email": user.email,
        "username": user.username,
        "password": hashed_password,
        "verified": False,
        "token": token
    }
    collection.insert_one(dbUser)
    
    if not testing:
        await send_verification_email(user.email, token)

    return {"message": "User registered successfully! Please check your email to verify your account."}
    
@app.post("/login")
def login_user(user: UserLogin, testing: bool = False):
    collection = get_user_collection(testing)
    dbUser = collection.find_one({"username": user.username})
    
    if not dbUser:
        print("User not found in DB!")
        raise HTTPException(status_code=400, detail="Invalid username or password")

    if not dbUser.get("verified", True):
        raise HTTPException(status_code=400, detail="Email not verified. Please check your inbox.")

    if not verify_password(user.password, dbUser["password"]):
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

@app.get("/dailypuzzle/{date}")
def get_daily_puzzle(date: str, testing: bool = False):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    collection = get_daily_puzzle_collection(testing)
    puzzle = collection.find_one({"date": date})
    
    if not puzzle:
        raise HTTPException(status_code=404, detail="No puzzle available")

    return {"name" : puzzle["name"], "description" : puzzle["description"], "tests" : puzzle["tests"]}

@app.get("/userfiles/{username}")
def get_user_files(username: str, testing: bool = False):
    collection = get_user_file_collection(testing)
    
    files_cursor = collection.find(
        {"owner": username},
        {"owner": 0,
         "_id": 0}
    )
    
    files = list(files_cursor)
    
    return {"files": files}

@app.post("/uploadfiles")
async def upload_user_files(fileList: UserFileList, testing: bool = False):
    collection = get_user_file_collection(testing)
    
    inserted_files = []
    for file in fileList.files:
        result = collection.insert_one(file.model_dump())
        
        inserted_files.append(str(result.inserted_id))
    
    return {"message": f"Successfully inserted {len(inserted_files)} files."}

@app.get("/")
def home():
    return {"message": "FastAPI MongoDB Backend is Running!"}
