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

    response = await register_user(user=user_data, testing=True)
    
    assert response["message"] == "User registered successfully! Please check your email to verify your account."

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

    with pytest.raises(HTTPException) as excinfo:
        await register_user(user=user_data, testing=True)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Username already taken"

@pytest.mark.asyncio
async def test_register_invalid_email():
    with pytest.raises(ValidationError):
        UserRegister(
            email="not-an-email",
            username="newuser",
            password="password123"
        )

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

    with pytest.raises(HTTPException) as excinfo:
        login_user(user=user_data, testing=True)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Invalid username or password"

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

    with pytest.raises(HTTPException) as excinfo:
        login_user(user=user_data, testing=True)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Email not verified. Please check your inbox."

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

    response = login_user(user=user_data, testing=True)

    assert response["message"] == "Login successful!"

def test_invalid_token():
    test_collection.insert_one({
        "username": "testuser", 
        "password": hash_password("mypassword"),
        "verified": False, 
        "token": "token"
    })

    with pytest.raises(HTTPException) as excinfo:
        verify_email("invalidtoken", testing=True)

    user = test_collection.find_one({"username": "testuser"})
    
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Invalid or expired token"
    assert user["verified"] == False
    assert "token" in user

def test_valid_token():
    test_collection.insert_one({
        "username": "testuser", 
        "password": hash_password("mypassword"),
        "verified": False, 
        "token": "token"
    })

    response = verify_email("token", testing=True)

    user = test_collection.find_one({"username": "testuser"})

    assert response["message"] == "Email verified successfully! You can now log in."
    assert user["verified"] == True
    assert "token" not in user

def test_get_daily_puzzle_valid_date():
    test_collection.insert_one({
        "date": "2024-03-05",
        "name": "Test Puzzle",
        "description": "Solve this challenge",
        "tests": ["add(2,5) == 7", "add(150,325) == 475"]
    })

    response = get_daily_puzzle("2024-03-05", testing=True)
    
    assert response == {
        "name": "Test Puzzle",
        "description": "Solve this challenge",
        "tests": ["add(2,5) == 7", "add(150,325) == 475"]
    }

def test_get_daily_puzzle_invalid_date_format():
    with pytest.raises(HTTPException) as excinfo:
        get_daily_puzzle("05-03-2024", testing=True)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Invalid date format. Use YYYY-MM-DD."

def test_get_daily_puzzle_not_found():
    with pytest.raises(HTTPException) as excinfo:
        get_daily_puzzle("2024-03-06", testing=True)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "No puzzle available"

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

    response = get_user_files("testuser", testing=True)["files"]

    assert len(response) == 2
    assert all("owner" not in file for file in response)
    assert all("_id" not in file for file in response)
    assert response[0]["name"] == "file1"
    assert response[1]["purpose"] == "playground"

def test_get_user_files_empty():
    response = get_user_files("nonexistentuser", testing=True)["files"]

    assert len(response) == 0

@pytest.mark.asyncio
async def test_upload_user_files():
    file_data = UserFileList(
        files=[
            UserFile(owner="testuser", content="def add(x, y):\n    return x + y", name="file1", purpose="daily puzzle"),
            UserFile(owner="testuser", content="x = 123", name="file2", purpose="playground")
        ]
    )

    response = await upload_user_files(fileList=file_data, testing=True)

    assert response["message"] == "Successfully inserted 2 files."
    
    assert test_collection.count_documents({"owner": "testuser"}) == 2
