import pytest
from fastapi.testclient import TestClient
from main import app
from config import mock_collection
from utils import hash_password, create_access_token
from models import *
client = TestClient(app)

@pytest.fixture(scope="session")
def auth_token():
    return create_access_token("testuser")

@pytest.fixture(scope="session")
def tutor_token():
    return create_access_token("testtutor")

@pytest.fixture(scope="function", autouse=True)
def clean_db():
    mock_collection.delete_many({})  # Clear the database before and after each test
    yield
    mock_collection.delete_many({})

@pytest.mark.asyncio
async def test_register_user():
    user_data = UserRegister(
        email="testuser@gmail.com",
        username="testuser",
        password="strongpassword"
    )

    response = client.post("/register", json=user_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "User registered successfully! Please check your email to verify your account."

@pytest.mark.asyncio
async def test_register_duplicate_user():
    mock_collection.insert_one({
        "username": "testuser", 
        "email": "test@example.com", 
        "password": hash_password("password")
    })
    
    user_data = UserRegister(
        email="test2@gmail.com", 
        username="testuser", 
        password="anotherpassword"
    )

    response = client.post("/register", json=user_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Username already taken"

def test_register_invalid_email():
    user_data = {
        "email": "not-an-email",
        "username": "newuser",
        "password": "password123"
    }

    response = client.post("/register", json=user_data, params={"testing": "True"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email format"

def test_login_invalid_password():
    mock_collection.insert_one({
        "username": "testuser", 
        "password": hash_password("correctpassword"), 
        "verified": True
    })

    user_data = UserLogin(
        username="testuser",
        password="wrongpassword"
    )

    response = client.post("/login", json=user_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid username or password"

def test_login_unverified_email():
    mock_collection.insert_one({
        "username": "unverified_user", 
        "password": hash_password("password"),
        "verified": False
    })

    user_data = UserLogin(
        username="unverified_user", 
        password="password"
    )

    response = client.post("/login", json=user_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Email not verified. Please check your inbox."

def test_login_success():
    mock_collection.insert_one({
        "username": "testuser", 
        "password": hash_password("mypassword"), 
        "verified": True
    })

    user_data = UserLogin(
        username="testuser", 
        password="mypassword"
    )

    response = client.post("/login", json=user_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "Login successful!"

def test_invalid_token():
    mock_collection.insert_one({
        "username": "testuser", 
        "password": hash_password("mypassword"),
        "verified": False, 
        "token": "token"
    })

    response = client.get("/verify/invalidtoken?testing=True")

    user = mock_collection.find_one({"username": "testuser"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired token"
    assert user["verified"] == False
    assert "token" in user

def test_valid_token():
    mock_collection.insert_one({
        "username": "testuser", 
        "password": hash_password("mypassword"),
        "verified": False, 
        "token": "token"
    })

    response = client.get("/verify/token?testing=True")

    user = mock_collection.find_one({"username": "testuser"})

    assert response.status_code == 200
    assert response.json()["message"] == "Email verified successfully! You can now log in."
    assert user["verified"] == True
    assert "token" not in user

def test_get_daily_puzzle_valid_date(auth_token):
    mock_collection.insert_one({
        "date": "2024-03-05",
        "name": "Test Puzzle",
        "description": "Solve this challenge",
        "tests": ["add(2,5) == 7", "add(150,325) == 475"],
        "room" : "ABCDEF"
    })

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/daily-puzzle/ABCDEF/2024-03-05?testing=True", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "name": "Test Puzzle",
        "description": "Solve this challenge",
        "tests": ["add(2,5) == 7", "add(150,325) == 475"]
    }

def test_get_daily_puzzle_invalid_date_format(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/daily-puzzle/ABCDEF/05-03-2024?testing=True", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid date format. Use YYYY-MM-DD."

def test_get_daily_puzzle_not_found(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/daily-puzzle/ABCDEF/2024-03-06?testing=True", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "No puzzle available"

def test_get_user_files_success(auth_token):
    mock_collection.insert_one({
        "owner": "testuser",
        "content": "def add(x, y):\nreturn x + y",
        "name": "file1",
        "purpose": "daily puzzle",
        "room": "ABCDEF"
    })
    mock_collection.insert_one({
        "owner": "testuser",
        "content": "x = 123",
        "name": "file2",
        "purpose": "playground",
        "room": "ABCDEF"
    })

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/user-files/ABCDEF/testuser?testing=True", headers=headers)

    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) == 2
    assert all("_id" not in file for file in files)
    assert files[0]["name"] == "file1"
    assert files[1]["purpose"] == "playground"

def test_get_user_files_empty(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/user-files/ABCDEF/testuser?testing=True", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["files"]) == 0

@pytest.mark.asyncio
async def test_upload_user_files(auth_token):
    file_data = UserFileList(
        files=[UserFile(owner="testuser", content="def add(x, y):\n    return x + y", name="file1", purpose="daily puzzle"),
               UserFile(owner="testuser", content="x = 123", name="file2", purpose="playground")],
        room="ABCDEF"
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/upload-files", json=file_data.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "Successfully updated 0 files, inserted 2 new files."
    assert mock_collection.count_documents({"owner": "testuser", "room": "ABCDEF"}) == 2

@pytest.mark.asyncio
async def test_upload_user_files_update(auth_token):
    mock_collection.insert_one({
        "owner": "testuser",
        "content": "old content",
        "name": "file1",
        "purpose": "purpose",
        "room": "ABCDEF"
    })
    
    updated_file_data = UserFileList(
        files=[UserFile(owner="testuser", content="new content", name="file1", purpose="purpose")],
        room="ABCDEF"
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/upload-files", json=updated_file_data.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200
    assert "updated 1" in response.json()["message"]
    assert "inserted 0" in response.json()["message"]

    updated_file = mock_collection.find_one({"owner": "testuser", "room": "ABCDEF", "name": "file1"})
    
    assert updated_file is not None
    assert updated_file["content"] == "new content"
    assert mock_collection.count_documents({"owner": "testuser", "room": "ABCDEF", "name": "file1"}) == 1

def test_get_lectures_success(auth_token):
    mock_collection.insert_one({
        "difficulty": "easy",
        "title": "Intro to Python",
        "slides": [{"name": "slide1", "content": "Content of slide 1"}],
        "quiz": [{"question": "What is 2+2?", "answer": "4", "options": ["3", "4", "5", "6"]}],
        "required": [],
        "passmark" : 50,
        "room": "ABCDEF"
    })
    mock_collection.insert_one({
        "difficulty": "easy",
        "title": "Basic Data Structures",
        "slides": [{"name": "slide1", "content": "Content of slide 1"}],
        "quiz": [{"question": "What is a list?", "answer": "A collection", "options": ["A number", "A collection", "A string"]}],
        "required": ["Intro to Python"],
        "passmark" : 100,
        "room": "ABCDEF"
    })

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/lectures/ABCDEF/easy?testing=True", headers=headers)

    assert response.status_code == 200
    lectures = response.json()["lectures"]
    print(lectures)
    assert len(lectures) == 2
    assert lectures[0]["title"] == "Intro to Python"
    assert lectures[1]["title"] == "Basic Data Structures"
    assert lectures[0]["difficulty"] == "easy"
    assert len(lectures[0]["slides"]) == 1
    assert len(lectures[0]["quiz"]) == 1
    assert len(lectures[0]["required"]) == 0
    assert len(lectures[1]["required"]) == 1

def test_get_lectures_no_matches(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/lectures/ABCDEF/advanced?testing=True", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "No lectures found for the given difficulty."

def test_get_guided_projects_success(auth_token):
    mock_collection.insert_one({
        "name": "Simple Greeting Program",
        "description": "Write a Python program that asks for the user's name and then prints a greeting message.",
        "difficulty": "easy",
        "steps": [
            {
                "title": "Create a function to greet the user",
                "description": "Write a function that asks for the user's name and stores it in a variable.",
                "code": "def greet_user():\n    name = ____\n    print('Hello, ' + name + '!')",
                "options": [
                    "input('What is your name? ')",
                    "'John'",
                    "42"
                ],
                "answer": "input('What is your name? ')"
            },
            {
                "title": "Call the greet_user() function",
                "description": "Call the greet_user function to display the greeting message to the user.",
                "code": "____",
                "options": [
                    "greet_user()",
                    "print('Hello World')",
                    "input('Press enter to continue')"
                ],
                "answer": "greet_user()"
            }
        ],
        "hints": [
            "Use the `input()` function to get the user's name.",
            "Make sure to call the function `greet_user()` to execute the greeting."
        ],
        "solution": "def greet_user():\n    name = input('What is your name? ')\n    print('Hello, ' + name + '!')\n\ngreet_user()",
        "room": "ABCDEF"
    })

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/guided-projects/ABCDEF?testing=True", headers=headers)

    assert response.status_code == 200
    guided_projects = response.json()["guidedProjects"]

    assert len(guided_projects) == 1
    assert guided_projects[0]["name"] == "Simple Greeting Program"
    assert guided_projects[0]["description"] == "Write a Python program that asks for the user's name and then prints a greeting message."
    assert guided_projects[0]["difficulty"] == "easy"
    
    steps = guided_projects[0]["steps"]
    assert len(steps) == 2
    assert len(steps[0]["options"]) == 3
    
def test_get_guided_projects_not_found(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/guided-projects/ABCDEF?testing=True", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "No guided projects found."

def test_get_user_data_success(auth_token):
    mock_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": ["Intro 1"],
            "projects": [],
            "puzzles": ["2025-03-10", "2025-03-12"]
        },
        "room": "ABCDEF",
        "level": "easy"
    })

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/user-data/testuser/ABCDEF?testing=True", headers=headers)

    assert response.status_code == 200
    user_data = response.json()

    assert user_data["username"] == "testuser"
    assert len(user_data["completions"]["puzzles"]) == 2

def test_get_user_data_not_found(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/user-data/testuser/ABCDEF?testing=True", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "No user data found"

def test_get_user_data_many(auth_token):
    mock_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": ["Intro 1"],
            "projects": [],
            "puzzles": ["2025-03-10", "2025-03-12"]
        },
        "room": "ABCDEF",
        "level": "easy"
    })
    mock_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": [],
            "projects": ["First Proj"],
            "puzzles": ["2025-03-12"]
        },
        "room": "ABCDEF",
        "level": "easy"
    })

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/user-data/testuser/ABCDEF?testing=True", headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "More than one user data found -> problem :("

def test_create_user_data(auth_token):
    user_data = UserData(
        username="testuser",
        completions=CompletionData(
            lectures=[],
            projects=[],
            puzzles=[]
        ),
        room="ABCDEF",
        level="easy"
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/user-data", json=user_data.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "User data created successfully"

    created_data_count = mock_collection.count_documents({"username": "testuser", "room": "ABCDEF"})
    assert created_data_count == 1

def test_update_user_data(auth_token):
    mock_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": [],
            "projects": ["a"],
            "puzzles": []
        },
        "room": "ABCDEF",
        "level": "easy"
    })

    user_data = UserData(
        username="testuser",
        completions=CompletionData(
            lectures=["Intro 1"],
            projects=["a", "b", "c"],
            puzzles=["2025-03-10", "2025-03-12"]
        ),
        room="ABCDEF",
        level="easy"
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/user-data", json=user_data.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "User data updated successfully"

    user_data_count = mock_collection.count_documents({"username": "testuser", "room": "ABCDEF"})
    assert user_data_count == 1

    updated_user_data = mock_collection.find_one({"username": "testuser", "room": "ABCDEF"})
    assert len(updated_user_data["completions"]["projects"]) == 3
    assert updated_user_data["completions"]["puzzles"][1] == "2025-03-12"

def test_update_lecture_completion(auth_token):
    mock_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": ["Existing Lecture"],
            "projects": [],
            "puzzles": []
        },
        "room":"ABCDEF"
    })
    new_lecture_request = LectureCompletionRequest(
        username="testuser",
        room="ABCDEF",
        lecture="New Lecture"
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/update-lecture-completion", json=new_lecture_request.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "Lectures completion updated successfully"

    user_data = mock_collection.find_one({"username": "testuser"})
    assert "New Lecture" in user_data["completions"]["lectures"]
    assert len(user_data["completions"]["lectures"]) == 2

def test_update_lecture_completion_with_promotion(auth_token):
    mock_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": ["Existing Lecture"],
            "projects": [],
            "puzzles": []
        },
        "room":"ABCDEF",
        "level":"intermediate"
    })
    mock_collection.insert_one({
        "difficulty": "intermediate",
        "title": "New Lecture",
        "room":"ABCDEF"
    })
    new_lecture_request = LectureCompletionRequest(
        username="testuser",
        room="ABCDEF",
        lecture="New Lecture"
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/update-lecture-completion", json=new_lecture_request.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "Promoted to advanced level"

def test_update_project_completion(auth_token):
    mock_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": [],
            "projects": ["Existing Project"],
            "puzzles": []
        },
        "room":"ABCDEF"
    })

    new_project_request = ProjectCompletionRequest(
        username="testuser",
        room="ABCDEF",
        project="New Project"
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/update-project-completion", json=new_project_request.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "Projects completion updated successfully"

    user_data = mock_collection.find_one({"username": "testuser"})
    assert "New Project" in user_data["completions"]["projects"]
    assert len(user_data["completions"]["projects"]) == 2

def test_update_puzzle_completion(auth_token):
    mock_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": [],
            "projects": [],
            "puzzles": ["2025-03-10"]
        },
        "room":"ABCDEF"
    })

    new_puzzle_request = PuzzleCompletionRequest(
        username="testuser",
        room="ABCDEF",
        puzzle="2025-03-12"
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/update-puzzle-completion", json=new_puzzle_request.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "Puzzles completion updated successfully"

    user_data = mock_collection.find_one({"username": "testuser"})
    assert "2025-03-12" in user_data["completions"]["puzzles"]
    assert len(user_data["completions"]["puzzles"]) == 2

def test_update_lecture_completion_no_changes(auth_token):
    mock_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": ["Same Lecture"],
            "projects": [],
            "puzzles": []
        },
        "room":"ABCDEF"
    })

    new_lecture_request = LectureCompletionRequest(
        username="testuser",
        room="ABCDEF",
        lecture="Same Lecture"
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/update-lecture-completion", json=new_lecture_request.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "No changes made"

    user_data = mock_collection.find_one({"username": "testuser"})
    assert len(user_data["completions"]["lectures"]) == 1

def test_update_project_completion_no_changes(auth_token):
    mock_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": [],
            "projects": ["Same Project"],
            "puzzles": []
        },
        "room":"ABCDEF"
    })

    new_project_request = ProjectCompletionRequest(
        username="testuser",
        room="ABCDEF",
        project="Same Project"
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/update-project-completion", json=new_project_request.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "No changes made"

    user_data = mock_collection.find_one({"username": "testuser"})
    assert len(user_data["completions"]["projects"]) == 1

def test_update_puzzle_completion_no_changes(auth_token):
    mock_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": [],
            "projects": [],
            "puzzles": ["2025-03-10"]
        },
        "room":"ABCDEF"
    })

    new_puzzle_request = PuzzleCompletionRequest(
        username="testuser",
        room="ABCDEF",
        puzzle="2025-03-10"
    )

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/update-puzzle-completion", json=new_puzzle_request.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "No changes made"

    user_data = mock_collection.find_one({"username": "testuser"})
    assert len(user_data["completions"]["puzzles"]) == 1

def test_execute_code_successful(auth_token):
    code_request = CodeRequest(
        code="print(\"hello world\")"
    )
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/execute-code", json=code_request.model_dump(), headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    assert "output" in response.json()
    assert response.json()["output"] == "hello world\n"

def test_execute_code_unsuccessful(auth_token):
    code_request = CodeRequest(
        code="badcode(abc)"
    )
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/execute-code", json=code_request.model_dump(), headers=headers)

    assert response.json()["status"] == "error"

def test_create_classroom_duplicate_name(tutor_token):
    mock_collection.insert_one({
        "owner": "boss", 
        "name": "test-clasroom", 
        "capacity": 3
    })
    
    room_request = RoomData(
        owner="testtutor",
        name="test-clasroom",
        capacity=1
    )

    headers = {"Authorization": f"Bearer {tutor_token}"}
    response = client.post("/create-room", json=room_request.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Name for classroom already taken"

def test_create_classroom_duplicate_code(tutor_token):
    mock_collection.insert_one({
        "owner": "testtutor", 
        "name": "test-clasroom", 
        "capacity": 3,
        "code": "ABC123"
    })

    room_request = RoomData(
        owner="testtutor",
        name="second-clasroom",
        capacity=1
    ) 
    # Default access code is hardcoded as ABC123 for testing in main function

    headers = {"Authorization": f"Bearer {tutor_token}"}
    response = client.post("/create-room", json=room_request.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200

    assert response.json()["code"] != 'ABC123'

    count = mock_collection.count_documents({"code": "ABC123"})
    assert count == 1


def test_create_classroom_success(tutor_token):
    room_request = RoomData(
        owner="testtutor",
        name="test-clasroom",
        capacity=1
    )

    headers = {"Authorization": f"Bearer {tutor_token}"}
    response = client.post("/create-room", json=room_request.model_dump(), params={"testing": "True"}, headers=headers)

    assert response.status_code == 200

    count = mock_collection.count_documents({"name": "test-clasroom"})
    assert count == 1


@pytest.mark.asyncio
async def test_register_tutor():
    tutor_data = TutorRegister(
        email="testtutor@gmail.com",
        username="testuser",
        password="strongpassword",
        type="Teacher",
        institution="Test High School"
    )

    response = client.post("/register-tutor", json=tutor_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "Tutor registered successfully! Please check your email to verify your account."

@pytest.mark.asyncio
async def test_register_duplicate_tutor():
    mock_collection.insert_one({
        "username": "testtutor", 
        "email": "test@example.com", 
        "password": hash_password("password")
    })
    
    tutor_data = TutorRegister(
        email="test2@gmail.com", 
        username="testtutor", 
        password="anotherpassword",
        type="Parent",
        institution="No institution"
    )

    response = client.post("/register-tutor", json=tutor_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Tutor username already taken"

def test_register_invalid_email_tutor():
    tutor_data = TutorRegister(
        email="not-an-email", 
        username="testtutor", 
        password="anotherpassword",
        type="Parent",
        institution="No institution"
    )

    response = client.post("/register-tutor", json=tutor_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email format"

def test_login_tutor_invalid_password():
    mock_collection.insert_one({
        "username": "testtutor", 
        "password": hash_password("correctpassword"), 
        "verified": True
    })

    tutor_data = UserLogin(
        username="testtutor",
        password="wrongpassword"
    )

    response = client.post("/login-tutor", json=tutor_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid username or password"

def test_login_tutor_unverified_email():
    mock_collection.insert_one({
        "username": "unverified_tutor", 
        "password": hash_password("password"),
        "verified": False
    })

    tutor_data = UserLogin(
        username="unverified_tutor", 
        password="password"
    )

    response = client.post("/login-tutor", json=tutor_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Email not verified. Please check your inbox."

def test_login_tutor_not_approved():
    mock_collection.insert_one({
        "username": "unapproved_tutor", 
        "password": hash_password("password"),
        "approved": False
    })

    tutor_data = UserLogin(
        username="unapproved_tutor", 
        password="password"
    )

    response = client.post("/login-tutor", json=tutor_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Account not approved yet. Please wait until notified or contact an admin."

def test_login_tutor_success():
    mock_collection.insert_one({
        "username": "testtutor", 
        "password": hash_password("mypassword"), 
        "verified": True
    })

    tutor_data = UserLogin(
        username="testtutor", 
        password="mypassword"
    )

    response = client.post("/login-tutor", json=tutor_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "Login successful!"

def test_get_single_room(tutor_token):
    mock_collection.insert_one({
        "owner": "testtutor", 
        "name": "testroom", 
        "capacity": 2
    })

    headers = {"Authorization": f"Bearer {tutor_token}"}
    response = client.get("/rooms/testtutor?testing=True", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["rooms"]) == 1
    assert response.json()["rooms"][0]["name"] == "testroom"

def test_get_multiple_rooms(tutor_token):
    mock_collection.insert_one({
        "owner": "testtutor", 
        "name": "testroom", 
        "capacity": 2
    })
    mock_collection.insert_one({
        "owner": "testtutor", 
        "name": "testroom2", 
        "capacity": 4
    })

    headers = {"Authorization": f"Bearer {tutor_token}"}
    response = client.get("/rooms/testtutor?testing=True", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["rooms"]) == 2

def test_get_no_rooms(tutor_token):
    headers = {"Authorization": f"Bearer {tutor_token}"}
    response = client.get("/rooms/testtutor?testing=True", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["rooms"]) == 0

def test_delete_no_room(tutor_token):
    headers = {"Authorization": f"Bearer {tutor_token}"}
    response = client.delete("/delete-room/ABCDEF?testing=True", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"

def test_delete_room(tutor_token):
    mock_collection.insert_one({
        "owner": "testtutor", 
        "name": "testroom", 
        "capacity": 2,
        "code": "ABCDEF"
    })

    count = mock_collection.count_documents({"code": "ABCDEF"})
    assert count == 1

    headers = {"Authorization": f"Bearer {tutor_token}"}
    response = client.delete("/delete-room/ABCDEF?testing=True", headers=headers)
    
    assert response.status_code == 200
    count = mock_collection.count_documents({"code": "ABCDEF"})
    assert count == 0