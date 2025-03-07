from pydantic import BaseModel, EmailStr
from typing import List

class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserFile(BaseModel):
    owner: str
    content: str
    name: str
    purpose: str

class UserFileList(BaseModel):
    files: List[UserFile]

