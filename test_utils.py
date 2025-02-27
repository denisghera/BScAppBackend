from utils import hash_password, verify_password, generate_unique_token

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

