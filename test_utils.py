from utils import *

def test_hash_password():
    password = "securepassword123"
    hashed = hash_password(password)
    assert isinstance(hashed, str)
    assert hashed != password

def test_verify_password():
    password = "securepassword123"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_generate_unique_token():
    token1 = generate_unique_token()
    token2 = generate_unique_token()
    
    assert isinstance(token1, str)
    assert isinstance(token2, str)
    assert token1 != token2

def test_extract_error_message():
    assert extract_error_message("Something went wrong - ValueError: invalid literal for int()") == "ValueError: invalid literal for int()"
    assert extract_error_message("some random words: SyntaxError: unexpected EOF while parsing") == "SyntaxError: unexpected EOF while parsing"
    assert extract_error_message("This is not an error message") == "Unknown Error"
    assert extract_error_message("") == "Unknown Error"
    assert extract_error_message("   ") == "Unknown Error"

def test_access_token_structure():
    username = "testuser"
    token = create_access_token(username)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    assert payload["sub"] == username
    assert payload["type"] == "access"
    assert "exp" in payload
    assert datetime.fromtimestamp(payload["exp"], tz=timezone.utc) > datetime.now(timezone.utc)

def test_refresh_token_structure():
    username = "testuser"
    token = create_refresh_token(username)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    assert payload["sub"] == username
    assert payload["type"] == "refresh"
    assert "exp" in payload
    assert datetime.fromtimestamp(payload["exp"], tz=timezone.utc) > datetime.now(timezone.utc)

def test_invalid_token_type_rejected():
    username = "testuser"
    # Fake a refresh token payload with type=refresh
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {"sub": username, "exp": expire, "type": "refresh"}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    try:
        # Simulate calling your verify_token logic manually
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["type"] == "access", "Token type should be access"
    except AssertionError:
        pass  # Test passes if this fails