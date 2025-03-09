import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app, register_user, login_user, verify_email, get_daily_puzzle, get_user_files, upload_user_files
from config import test_collection
from utils import hash_password
from models import UserRegister, UserLogin, UserFileList, UserFile
from pydantic import ValidationError

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

    response = client.get("/dailypuzzle/2024-03-05?testing=True")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Test Puzzle",
        "description": "Solve this challenge",
        "tests": ["add(2,5) == 7", "add(150,325) == 475"]
    }

def test_get_daily_puzzle_invalid_date_format():
    response = client.get("/dailypuzzle/05-03-2024?testing=True")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid date format. Use YYYY-MM-DD."

def test_get_daily_puzzle_not_found():
    response = client.get("/dailypuzzle/2024-03-06?testing=True")

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

    response = client.get("/userfiles/testuser?testing=True")

    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) == 2
    assert all("_id" not in file for file in files)
    assert files[0]["name"] == "file1"
    assert files[1]["purpose"] == "playground"

def test_get_user_files_empty():
    response = client.get("/userfiles/nonexistentuser?testing=True")

    assert response.status_code == 200
    assert len(response.json()["files"]) == 0

@pytest.mark.asyncio
async def test_upload_user_files():
    file_data = UserFileList(
        files=[UserFile(owner="testuser", content="def add(x, y):\n    return x + y", name="file1", purpose="daily puzzle"),
               UserFile(owner="testuser", content="x = 123", name="file2", purpose="playground")]
    )

    response = client.post("/uploadfiles", json=file_data.model_dump(), params={"testing": "True"})

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

    response = client.post("/uploadfiles", json=updated_file_data.model_dump(), params={"testing": "True"})

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
        "required": []
    })
    test_collection.insert_one({
        "difficulty": "easy",
        "title": "Basic Data Structures",
        "slides": [{"name": "slide1", "content": "Content of slide 1"}],
        "quiz": [{"question": "What is a list?", "answer": "A collection", "options": ["A number", "A collection", "A string"]}],
        "required": ["Intro to Python"]
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
