from fastapi import FastAPI, HTTPException
from email_validator import validate_email, EmailNotValidError
from datetime import datetime
from pymongo import UpdateOne
from config import *
from models import *
from utils import *

app = FastAPI()

def get_user_collection(testing: bool):
    return test_collection if testing else users_collection

def get_daily_puzzle_collection(testing: bool):
    return test_collection if testing else daily_puzzle_collection

def get_user_file_collection(testing: bool):
    return test_collection if testing else user_file_collection

def get_lecture_collection(testing: bool):
    return test_collection if testing else lecture_collection

def get_guided_projects_collection(testing:bool):
    return test_collection if testing else guided_projects_collection

@app.post("/register")
async def register_user(user: UserRegister, testing: bool = False):
    collection = get_user_collection(testing)
    try:
        validate_email(user.email)
    except EmailNotValidError:
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

@app.get("/daily-puzzle/{date}")
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

@app.get("/user-files/{username}")
def get_user_files(username: str, testing: bool = False):
    collection = get_user_file_collection(testing)
    
    files_cursor = collection.find(
        {"owner": username},
        {"_id": 0}
    )
    
    files = list(files_cursor)
    
    return {"files": files}

@app.post("/upload-files")
async def upload_user_files(fileList: UserFileList, testing: bool = False):
    collection = get_user_file_collection(testing)
    
    operations = []
    
    for file in fileList.files:
        operations.append(
            UpdateOne(
                {"owner": file.owner, "name": file.name, "purpose": file.purpose},
                {"$set": file.model_dump()},
                upsert=True
            )
        )
    
    if operations:
        result = collection.bulk_write(operations)
    
    return {
        "message": f"Successfully updated {result.matched_count} files, inserted {result.upserted_count} new files."
    }

@app.get("/lectures/{difficulty}")
def get_lectures(difficulty: str, testing: bool = False):
    collection = get_lecture_collection(testing)
    
    count = collection.count_documents({"difficulty": difficulty})
    
    if count == 0:
        raise HTTPException(status_code=404, detail="No lectures found for the given difficulty.")
    
    lectures_cursor = collection.find({"difficulty": difficulty})

    lectures = []
    for lecture in lectures_cursor:
        lecture_data = LectureData(
            difficulty=lecture["difficulty"],
            title=lecture["title"],
            slides=[
                SlideData(
                    name=slide["name"], 
                    content=slide["content"]
                ) 
                for slide in lecture["slides"]
            ],
            quiz=[
                QuizData(
                    question=quiz["question"], 
                    answer=quiz["answer"], 
                    options=quiz["options"]
                ) 
                for quiz in lecture["quiz"]
            ],
            required=lecture["required"],
            passmark=lecture["passmark"]
        )
        lectures.append(lecture_data)
    
    return {"lectures": lectures}

@app.get("/guided-projects")
def get_guided_projects(testing: bool = False):
    collection = get_guided_projects_collection(testing)

    count = collection.count_documents({})

    if count == 0:
        raise HTTPException(status_code=404, detail="No guided projects found.")
    
    projects_cursor = collection.find({})

    guided_projects = []
    for project in projects_cursor:
        guided_project = GuidedProjectData(
            name=project['name'],
            description=project['description'],
            difficulty=project['difficulty'],
            steps=[
                StepData(
                    title=step['title'],
                    description=step['description'],
                    code=step['code'],
                    options=step['options']
                )
                for step in project['steps']
            ],
            hints=project['hints'],
            solution=project['solution']
        )
        guided_projects.append(guided_project)

    return {"guidedProjects": guided_projects}

@app.get("/")
def home():
    return {"message": "FastAPI MongoDB Backend is Running!"}
