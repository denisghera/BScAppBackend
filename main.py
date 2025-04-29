from fastapi import FastAPI, HTTPException
from email_validator import validate_email, EmailNotValidError
from datetime import datetime
from pymongo import UpdateOne
from config import *
from models import *
from utils import *
import subprocess
import uuid

app = FastAPI()

def get_user_credentials_collection(testing: bool):
    return mock_collection if testing else user_credentials_collection

def get_daily_puzzle_collection(testing: bool):
    return mock_collection if testing else daily_puzzle_collection

def get_user_file_collection(testing: bool):
    return mock_collection if testing else user_file_collection

def get_lecture_collection(testing: bool):
    return mock_collection if testing else lecture_collection

def get_guided_projects_collection(testing: bool):
    return mock_collection if testing else guided_projects_collection

def get_user_data_collection(testing: bool):
    return mock_collection if testing else user_data_collection

def get_tutor_credentials_collection(testing: bool):
    return mock_collection if testing else tutor_credentials_collection

def get_classroom_data_collection(testing: bool):
    return mock_collection if testing else classroom_data_collection

@app.post("/register")
async def register_user(user: UserRegister, testing: bool = False):
    collection = get_user_credentials_collection(testing)
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
        await send_verification_email(user.email, token, 'user')

    return {"message": "User registered successfully! Please check your email to verify your account."}
    
@app.post("/login")
def login_user(user: UserLogin, testing: bool = False):
    collection = get_user_credentials_collection(testing)
    dbUser = collection.find_one({"username": user.username})
    
    if dbUser["username"] == "testuser":
        raise HTTPException(status_code=400, detail="Cannot use the test user")
    
    if not dbUser or not verify_password(user.password, dbUser["password"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    if not dbUser.get("verified", True):
        raise HTTPException(status_code=400, detail="Email not verified. Please check your inbox.")
    
    access_token = create_access_token(dbUser["username"])
    refresh_token = create_refresh_token(dbUser["username"])
    return {
      "message": "Login successful!",
      "access_token": access_token,
      "refresh_token": refresh_token,
      "token_type": "bearer"
    }

@app.get("/verify/{token}")
def verify_email(token: str, testing: bool = False):
    collection = get_user_credentials_collection(testing)
    user = collection.find_one({"token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    collection.update_one({"token": token}, {"$set": {"verified": True}, "$unset": {"token": ""}})

    return {"message": "Email verified successfully! You can now log in."}

@app.post("/refresh")
def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        # Check that this refresh token is still valid (optional: store in DB)
        new_access_token = create_access_token(username)
        return {"access_token": new_access_token, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.get("/daily-puzzle/{room}/{date}")
def get_daily_puzzle(room: str, date: str, testing: bool = False, _: str = Depends(verify_token)):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    collection = get_daily_puzzle_collection(testing)
    puzzle = collection.find_one({"date": date, "room": room})
    
    if not puzzle:
        raise HTTPException(status_code=404, detail="No puzzle available")

    return {"name" : puzzle["name"], "description" : puzzle["description"], "tests" : puzzle["tests"]}

@app.get("/user-files/{room}/{username}")
def get_user_files(room: str, username: str, testing: bool = False, current_user: str = Depends(verify_token)):
    collection = get_user_file_collection(testing)
    
    if username != current_user:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another user's files")
    
    files_cursor = collection.find(
        {"room" : room, "owner" : username},
        {"_id": 0}
    )
    
    files = list(files_cursor)
    
    return {"files": files}

@app.post("/upload-files")
async def upload_user_files(fileList: UserFileList, testing: bool = False, current_user: str = Depends(verify_token)):
    collection = get_user_file_collection(testing)
    
    operations = []
    
    for file in fileList.files:
        # Skip files that are mistakenly/maliciously of another user's
        if file.owner != current_user:
            continue
        operations.append(
            UpdateOne(
                {"owner": file.owner, "room": fileList.room, "name": file.name, "purpose": file.purpose},
                {"$set": file.model_dump()},
                upsert=True
            )
        )
    
    if operations:
        result = collection.bulk_write(operations)
    else:
        return {"message": "No operations"}
    
    return {
        "message": f"Successfully updated {result.matched_count} files, inserted {result.upserted_count} new files."
    }

@app.get("/lectures/{room}/{difficulty}")
def get_lectures(room: str, difficulty: str, testing: bool = False, _: str = Depends(verify_token)):
    collection = get_lecture_collection(testing)
    
    count = collection.count_documents({"room": room, "difficulty": difficulty})
    
    if count == 0:
        raise HTTPException(status_code=404, detail="No lectures found for the given difficulty.")
    
    lectures_cursor = collection.find({"room": room, "difficulty": difficulty})

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

@app.get("/guided-projects/{room}")
def get_guided_projects(room: str, testing: bool = False, _: str = Depends(verify_token)):
    collection = get_guided_projects_collection(testing)

    count = collection.count_documents({"room": room})

    if count == 0:
        raise HTTPException(status_code=404, detail="No guided projects found.")
    
    projects_cursor = collection.find({"room": room})

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
                    options=step['options'],
                    answer=step['answer']
                )
                for step in project['steps']
            ],
            hints=project['hints'],
            solution=project['solution']
        )
        guided_projects.append(guided_project)

    return {"guidedProjects": guided_projects}

@app.get("/user-data/{username}/{room}")
def get_user_data(username: str, room: str, testing: bool = False, current_user: str = Depends(verify_token)):
    collection = get_user_data_collection(testing)

    if username != current_user:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another user's data")

    count = collection.count_documents({"username" : username, "room": room})

    if count == 0:
        raise HTTPException(status_code=404, detail="No user data found")
    elif count > 1:
        raise HTTPException(status_code=409, detail="More than one user data found -> problem :(")

    user_data_cursor = collection.find_one({"username" : username, "room": room})
    user_data = UserData(
            username=user_data_cursor.get("username"),
            completions=CompletionData(
                lectures=user_data_cursor["completions"]["lectures"],
                projects=user_data_cursor["completions"]["projects"],
                puzzles=user_data_cursor["completions"]["puzzles"]
            ),
            room=user_data_cursor.get("room")
    )

    return user_data

@app.post("/user-data")
def create_or_update_user_data(user_data: UserData, testing: bool = False, current_user: str = Depends(verify_token)):
    collection = get_user_data_collection(testing)

    if user_data.username != current_user:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another user's data")

    result = collection.update_one(
        {"username": user_data.username, "room": user_data.room},
        {"$set": {
            "completions.lectures": user_data.completions.lectures,
            "completions.projects": user_data.completions.projects,
            "completions.puzzles": user_data.completions.puzzles
        }},
        upsert=True  # Creates a new document if one doesn’t exist
    )

    if result.matched_count:
        return {"message": "User data updated successfully"}
    else:
        return {"message": "User data created successfully"}

@app.post("/update-lecture-completion")
def update_lecture_completion(request: LectureCompletionRequest, testing: bool = False, current_user: str = Depends(verify_token)):
    collection = get_user_data_collection(testing)

    if request.username != current_user:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another user's data")

    result = collection.update_one(
        {"username": request.username, "room": request.room},
        {"$addToSet": {"completions.lectures": request.lecture}}
    )

    return {"message": "Lectures completion updated successfully"} if result.modified_count else {"message": "No changes made"}

@app.post("/update-project-completion")
def update_project_completion(request: ProjectCompletionRequest, testing: bool = False, current_user: str = Depends(verify_token)):
    collection = get_user_data_collection(testing)

    if request.username != current_user:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another user's data")

    result = collection.update_one(
        {"username": request.username, "room": request.room},
        {"$addToSet": {"completions.projects": request.project}}
    )
    
    return {"message": "Projects completion updated successfully"} if result.modified_count else {"message": "No changes made"}

@app.post("/update-puzzle-completion")
def update_puzzle_completion(request: PuzzleCompletionRequest, testing: bool = False, current_user: str = Depends(verify_token)):
    collection = get_user_data_collection(testing)

    if request.username != current_user:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another user's data")
    
    result = collection.update_one(
        {"username": request.username, "room": request.room},
        {"$addToSet": {"completions.puzzles": request.puzzle}}
    )
    
    return {"message": "Puzzles completion updated successfully"} if result.modified_count else {"message": "No changes made"}

@app.post("/execute-code")
def execute_code(request: CodeRequest):
    if not is_safe_code(request.code):
        return {"status": "error", "message": "Code contains disallowed imports"}
    
    temp_file = f"temp/temp_script_{uuid.uuid4().hex}.py"
    try:
        with open(temp_file, "w") as f:
            f.write(request.code)
        
        result = subprocess.run(["python", temp_file], capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            clean_error = extract_error_message(result.stderr)
            return {"status": "error", "message": clean_error}

        return {"status": "success", "output": result.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

@app.post("/register-tutor")
async def register_tutor(tutor: TutorRegister, testing: bool = False):
    collection = get_tutor_credentials_collection(testing)
    try:
        validate_email(tutor.email)
    except EmailNotValidError:
        raise HTTPException(status_code=400, detail="Invalid email format")

    if collection.find_one({"username": tutor.username}):
        raise HTTPException(status_code=400, detail="Tutor username already taken")

    if len(tutor.password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")
    hashed_password = hash_password(tutor.password)

    token = generate_unique_token()

    dbTutor = {
        "email": tutor.email,
        "username": tutor.username,
        "password": hashed_password,
        "type": tutor.type,
        "institution": tutor.institution,
        "verified": False,
        "token": token,
        "approved": False
    }
    collection.insert_one(dbTutor)
    
    if not testing:
        await send_verification_email(tutor.email, token, 'tutor')

    return {"message": "Tutor registered successfully! Please check your email to verify your account."}
    
@app.post("/login-tutor")
def login_tutor(tutor: UserLogin, testing: bool = False):
    collection = get_tutor_credentials_collection(testing)
    dbTutor = collection.find_one({"username": tutor.username})

    if dbTutor["username"] == "testtutor":
        raise HTTPException(status_code=400, detail="Cannot use the test tutor")
    
    if not dbTutor or not verify_password(tutor.password, dbTutor["password"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    if not dbTutor.get("verified", True):
        raise HTTPException(status_code=400, detail="Email not verified. Please check your inbox.")
    
    if not dbTutor.get("approved", True):
        raise HTTPException(status_code=400, detail="Account not approved yet. Please wait until notified or contact an admin.")
    
    access_token = create_access_token(dbTutor["username"])
    refresh_token = create_refresh_token(dbTutor["username"])
    return {
      "message": "Login successful!",
      "access_token": access_token,
      "refresh_token": refresh_token,
      "token_type": "bearer"
    }

@app.get("/verify-tutor/{token}")
def verify_tutor_email(token: str, testing: bool = False):
    collection = get_tutor_credentials_collection(testing)
    tutor = collection.find_one({"token": token})
    if not tutor:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    collection.update_one({"token": token}, {"$set": {"verified": True}, "$unset": {"token": ""}})

    return {"message": "Email verified successfully! Please wait for approval notification or contact an admin."}

@app.post("/create-room")
def create_room(request: RoomData, testing: bool = False, current_tutor: str = Depends(verify_tutor_token)):
    collection = get_classroom_data_collection(testing)

    if request.owner != current_tutor:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another tutor's rooms")

    count = collection.count_documents({"owner" : request.owner})

    if count == 4:
        raise HTTPException(status_code=400, detail="Room creation limit reached")

    if collection.find_one({"name": request.name}):
        raise HTTPException(status_code=400, detail="Name for classroom already taken")
    
    if testing:
        access_code = 'ABC123'
    else:
        access_code = generate_access_code()

    # Make sure code is unique
    while collection.find_one({"code": access_code}):
        access_code = generate_access_code()

    room_data = {
        "owner": request.owner,
        "name": request.name,
        "capacity": request.capacity,
        "code" : access_code
    }
    collection.insert_one(room_data)

    return {"message": "Classroom created with success!", "code": access_code}

@app.get("/rooms/{owner}")
def get_rooms(owner: str, testing: bool = False, current_tutor: str = Depends(verify_tutor_token)):
    collection = get_classroom_data_collection(testing)

    if owner != current_tutor:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another tutor's rooms")
    
    rooms_cursor = collection.find(
        {"owner": owner},
        {"_id": 0}
    )
    
    rooms = list(rooms_cursor)
    
    return {"rooms": rooms}

@app.get("/room/{code}")
def get_room_by_code(code: str, testing: bool = False, _: str = Depends(verify_token)):
    collection = get_classroom_data_collection(testing)

    room = collection.find_one(
        {"code": code},
        {"_id": 0}
    )

    if not room:
        raise HTTPException(status_code=404, detail="Room code doesn't exist")

    return room

@app.delete("/delete-room/{code}")
def delete_room_by_code(code: str, testing: bool = False, current_tutor: str = Depends(verify_tutor_token)):
    collection = get_classroom_data_collection(testing)

    room = collection.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.get("owner") != current_tutor:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another tutor's rooms")

    collection.delete_one({"code": code})
    
    return {"message": "Room deleted successfully"}

@app.get("/")
def home():
    return {"message": "FastAPI MongoDB Backend is Running!"}
