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