import pytest
from fastapi.testclient import TestClient
from main import app
from config import test_collection
from utils import hash_password
from models import *

client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def clean_db():
    test_collection.delete_many({})  # Clear the database before and after each test
    yield
    test_collection.delete_many({})

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
    test_collection.insert_one({
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
    test_collection.insert_one({
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
    test_collection.insert_one({
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
    test_collection.insert_one({
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
    test_collection.insert_one({
        "username": "testuser", 
        "password": hash_password("mypassword"),
        "verified": False, 
        "token": "token"
    })

    response = client.get("/verify/invalidtoken?testing=True")

    user = test_collection.find_one({"username": "testuser"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired token"
    assert user["verified"] == False
    assert "token" in user

def test_valid_token():
    test_collection.insert_one({
        "username": "testuser", 
        "password": hash_password("mypassword"),
        "verified": False, 
        "token": "token"
    })

    response = client.get("/verify/token?testing=True")

    user = test_collection.find_one({"username": "testuser"})

    assert response.status_code == 200
    assert response.json()["message"] == "Email verified successfully! You can now log in."
    assert user["verified"] == True
    assert "token" not in user

def test_get_daily_puzzle_valid_date():
    test_collection.insert_one({
        "date": "2024-03-05",
        "name": "Test Puzzle",
        "description": "Solve this challenge",
        "tests": ["add(2,5) == 7", "add(150,325) == 475"]
    })

    response = client.get("/daily-puzzle/2024-03-05?testing=True")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Test Puzzle",
        "description": "Solve this challenge",
        "tests": ["add(2,5) == 7", "add(150,325) == 475"]
    }

def test_get_daily_puzzle_invalid_date_format():
    response = client.get("/daily-puzzle/05-03-2024?testing=True")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid date format. Use YYYY-MM-DD."

def test_get_daily_puzzle_not_found():
    response = client.get("/daily-puzzle/2024-03-06?testing=True")

    assert response.status_code == 404
    assert response.json()["detail"] == "No puzzle available"

def test_get_user_files_success():
    test_collection.insert_one({
        "owner": "testuser",
        "content": "def add(x, y):\nreturn x + y",
        "name": "file1",
        "purpose": "daily puzzle"
    })
    test_collection.insert_one({
        "owner": "testuser",
        "content": "x = 123",
        "name": "file2",
        "purpose": "playground"
    })

    response = client.get("/user-files/testuser?testing=True")

    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) == 2
    assert all("_id" not in file for file in files)
    assert files[0]["name"] == "file1"
    assert files[1]["purpose"] == "playground"

def test_get_user_files_empty():
    response = client.get("/user-files/nonexistentuser?testing=True")

    assert response.status_code == 200
    assert len(response.json()["files"]) == 0

@pytest.mark.asyncio
async def test_upload_user_files():
    file_data = UserFileList(
        files=[UserFile(owner="testuser", content="def add(x, y):\n    return x + y", name="file1", purpose="daily puzzle"),
               UserFile(owner="testuser", content="x = 123", name="file2", purpose="playground")]
    )

    response = client.post("/upload-files", json=file_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "Successfully updated 0 files, inserted 2 new files."
    assert test_collection.count_documents({"owner": "testuser"}) == 2

@pytest.mark.asyncio
async def test_upload_user_files_update():
    test_collection.insert_one({
        "owner": "testuser",
        "content": "old content",
        "name": "file1",
        "purpose": "purpose"
    })
    
    updated_file_data = UserFileList(
        files=[UserFile(owner="testuser", content="new content", name="file1", purpose="purpose")]
    )

    response = client.post("/upload-files", json=updated_file_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert "updated 1" in response.json()["message"]
    assert "inserted 0" in response.json()["message"]

    updated_file = test_collection.find_one({"owner": "testuser", "name": "file1"})
    
    assert updated_file is not None
    assert updated_file["content"] == "new content"
    assert test_collection.count_documents({"owner": "testuser", "name": "file1"}) == 1

def test_get_lectures_success():
    test_collection.insert_one({
        "difficulty": "easy",
        "title": "Intro to Python",
        "slides": [{"name": "slide1", "content": "Content of slide 1"}],
        "quiz": [{"question": "What is 2+2?", "answer": "4", "options": ["3", "4", "5", "6"]}],
        "required": [],
        "passmark" : 50
    })
    test_collection.insert_one({
        "difficulty": "easy",
        "title": "Basic Data Structures",
        "slides": [{"name": "slide1", "content": "Content of slide 1"}],
        "quiz": [{"question": "What is a list?", "answer": "A collection", "options": ["A number", "A collection", "A string"]}],
        "required": ["Intro to Python"],
        "passmark" : 100
    })

    response = client.get("/lectures/easy?testing=True")

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

def test_get_lectures_no_matches():
    response = client.get("/lectures/advanced?testing=True")

    assert response.status_code == 404
    assert response.json()["detail"] == "No lectures found for the given difficulty."

def test_get_guided_projects_success():
    test_collection.insert_one({
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
        "solution": "def greet_user():\n    name = input('What is your name? ')\n    print('Hello, ' + name + '!')\n\ngreet_user()"
    })

    response = client.get("/guided-projects?testing=True")

    assert response.status_code == 200
    guided_projects = response.json()["guidedProjects"]

    assert len(guided_projects) == 1
    assert guided_projects[0]["name"] == "Simple Greeting Program"
    assert guided_projects[0]["description"] == "Write a Python program that asks for the user's name and then prints a greeting message."
    assert guided_projects[0]["difficulty"] == "easy"
    
    steps = guided_projects[0]["steps"]
    assert len(steps) == 2
    assert len(steps[0]["options"]) == 3
    
def test_get_guided_projects_not_found():
    response = client.get("/guided-projects?testing=True")

    assert response.status_code == 404
    assert response.json()["detail"] == "No guided projects found."

def test_get_user_data_success():
    test_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": ["Intro 1"],
            "projects": [],
            "puzzles": ["2025-03-10", "2025-03-12"]
        }
    })

    response = client.get("/user-data/testuser?testing=True")

    assert response.status_code == 200
    user_data = response.json()

    assert user_data["username"] == "testuser"
    assert len(user_data["completions"]["puzzles"]) == 2

def test_get_user_data_not_found():
    response = client.get("/user-data/nonexistinguser?testing=True")

    assert response.status_code == 404
    assert response.json()["detail"] == "No user data found -> problem :("

def test_get_user_data_many():
    test_collection.insert_one({
        "username": "testuserduplicate",
        "completions": {
            "lectures": ["Intro 1"],
            "projects": [],
            "puzzles": ["2025-03-10", "2025-03-12"]
        }
    })
    test_collection.insert_one({
        "username": "testuserduplicate",
        "completions": {
            "lectures": [],
            "projects": ["First Proj"],
            "puzzles": ["2025-03-12"]
        }
    })

    response = client.get("/user-data/testuserduplicate?testing=True")

    assert response.status_code == 409
    assert response.json()["detail"] == "More than one user data found -> problem :("

def test_create_user_data():
    user_data = UserData(
        username="testuser",
        completions=CompletionData(
            lectures=[],
            projects=[],
            puzzles=[]
        )
    )

    response = client.post("/user-data", json=user_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "User data created successfully"

    created_data_count = test_collection.count_documents({"username": "testuser"})
    assert created_data_count == 1

def test_update_user_data():
    test_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": [],
            "projects": ["a"],
            "puzzles": []
        }
    })

    user_data = UserData(
        username="testuser",
        completions=CompletionData(
            lectures=["Intro 1"],
            projects=["a", "b", "c"],
            puzzles=["2025-03-10", "2025-03-12"]
        )
    )

    response = client.post("/user-data", json=user_data.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "User data updated successfully"

    user_data_count = test_collection.count_documents({"username": "testuser"})
    assert user_data_count == 1

    updated_user_data = test_collection.find_one({"username": "testuser"})
    assert len(updated_user_data["completions"]["projects"]) == 3
    assert updated_user_data["completions"]["puzzles"][1] == "2025-03-12"

def test_update_lecture_completion():
    test_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": ["Existing Lecture"],
            "projects": [],
            "puzzles": []
        }
    })
    new_lecture_request = LectureCompletionRequest(
        username="testuser",
        lecture="New Lecture"
    )

    response = client.post("/update-lecture-completion", json=new_lecture_request.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "Lectures completion updated successfully"

    user_data = test_collection.find_one({"username": "testuser"})
    assert "New Lecture" in user_data["completions"]["lectures"]
    assert len(user_data["completions"]["lectures"]) == 2

def test_update_project_completion():
    test_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": [],
            "projects": ["Existing Project"],
            "puzzles": []
        }
    })

    new_project_request = ProjectCompletionRequest(
        username="testuser",
        project="New Project"
    )

    response = client.post("/update-project-completion", json=new_project_request.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "Projects completion updated successfully"

    user_data = test_collection.find_one({"username": "testuser"})
    assert "New Project" in user_data["completions"]["projects"]
    assert len(user_data["completions"]["projects"]) == 2

def test_update_puzzle_completion():
    test_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": [],
            "projects": [],
            "puzzles": ["2025-03-10"]
        }
    })

    new_puzzle_request = PuzzleCompletionRequest(
        username="testuser",
        puzzle="2025-03-12"
    )

    response = client.post("/update-puzzle-completion", json=new_puzzle_request.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "Puzzles completion updated successfully"

    user_data = test_collection.find_one({"username": "testuser"})
    assert "2025-03-12" in user_data["completions"]["puzzles"]
    assert len(user_data["completions"]["puzzles"]) == 2

def test_update_lecture_completion_no_changes():
    test_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": ["Same Lecture"],
            "projects": [],
            "puzzles": []
        }
    })

    new_lecture_request = LectureCompletionRequest(
        username="testuser",
        lecture="Same Lecture"
    )

    response = client.post("/update-lecture-completion", json=new_lecture_request.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "No changes made"

    user_data = test_collection.find_one({"username": "testuser"})
    assert len(user_data["completions"]["lectures"]) == 1

def test_update_project_completion_no_changes():
    test_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": [],
            "projects": ["Same Project"],
            "puzzles": []
        }
    })

    new_project_request = ProjectCompletionRequest(
        username="testuser",
        project="Same Project"
    )

    response = client.post("/update-project-completion", json=new_project_request.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "No changes made"

    user_data = test_collection.find_one({"username": "testuser"})
    assert len(user_data["completions"]["projects"]) == 1

def test_update_puzzle_completion_no_changes():
    test_collection.insert_one({
        "username": "testuser",
        "completions": {
            "lectures": [],
            "projects": [],
            "puzzles": ["2025-03-10"]
        }
    })

    new_puzzle_request = PuzzleCompletionRequest(
        username="testuser",
        puzzle="2025-03-10"
    )

    response = client.post("/update-puzzle-completion", json=new_puzzle_request.model_dump(), params={"testing": "True"})

    assert response.status_code == 200
    assert response.json()["message"] == "No changes made"

    user_data = test_collection.find_one({"username": "testuser"})
    assert len(user_data["completions"]["puzzles"]) == 1

def test_execute_code_successful():
    code_request = CodeRequest(
        code="print(\"hello world\")"
    )
    response = client.post("/execute-code", json=code_request.model_dump())

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    assert "output" in response.json()
    assert response.json()["output"] == "hello world\n"

def test_execute_code_unsuccessful():
    code_request = CodeRequest(
        code="badcode(abc)"
    )
    response = client.post("/execute-code", json=code_request.model_dump())

    assert response.json()["status"] == "error"