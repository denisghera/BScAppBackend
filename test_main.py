import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app, register_user, login_user, verify_email
from config import test_collection
from utils import hash_password

client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def clean_db():
    test_collection.delete_many({})
    yield
    test_collection.delete_many({})

@pytest.mark.asyncio
async def test_register_user():
    response = await register_user(email="testuser@gmail.com", username="testuser", password="strongpassword", testing=True)
    
    assert response["message"] == "User registered successfully! Please check your email to verify your account."

@pytest.mark.asyncio
async def test_register_duplicate_user():
    test_collection.insert_one({"username": "testuser", "email": "test@example.com", "password": hash_password("password")})
    
    with pytest.raises(HTTPException) as excinfo:
        await register_user(email="test2@gmail.com", username="testuser", password="anotherpassword", testing=True)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Username already taken"

@pytest.mark.asyncio
async def test_register_invalid_email():
    with pytest.raises(HTTPException) as excinfo:
        await register_user(email="not-an-email", username="newuser", password="password123", testing=True)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Invalid email format"

def test_login_invalid_password():
    test_collection.insert_one({"username": "testuser", "password": hash_password("correctpassword"), "verified": True})

    with pytest.raises(HTTPException) as excinfo:
        login_user(username="testuser", password="wrongpassword", testing=True)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Invalid username or password"

def test_login_unverified_email():
    test_collection.insert_one({"username": "unverified_user", "password": hash_password("password"), "verified": False})

    with pytest.raises(HTTPException) as excinfo:
        login_user(username="unverified_user", password="password", testing=True)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Email not verified. Please check your inbox."

def test_login_success():
    test_collection.insert_one({"username": "testuser", "password": hash_password("mypassword"), "verified": True})

    response = login_user(username="testuser", password="mypassword", testing=True)

    assert response["message"] == "Login successful!"

def test_invalid_token():
    test_collection.insert_one({"username": "testuser", "password": hash_password("mypassword"), "verified": False, "token": "token"})

    with pytest.raises(HTTPException) as excinfo:
        verify_email("invalidtoken", testing=True)

    user = test_collection.find_one({"username": "testuser"})
    
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Invalid or expired token"
    assert user["verified"] == False
    assert "token" in user

def test_valid_token():
    test_collection.insert_one({"username": "testuser", "password": hash_password("mypassword"), "verified": False, "token": "token"})

    response = verify_email("token", testing=True)

    user = test_collection.find_one({"username": "testuser"})

    assert response["message"] == "Email verified successfully! You can now log in."
    assert user["verified"] == True
    assert "token" not in user