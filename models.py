from pydantic import BaseModel, EmailStr
from typing import List

class UserRegister(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserFile(BaseModel):
    owner: str
    name: str
    content: str
    purpose: str

class UserFileList(BaseModel):
    files: List[UserFile]

class SlideData(BaseModel):
    name: str
    content: str

class QuizData(BaseModel):
    question: str
    answer: str
    options: List[str]

class LectureData(BaseModel):
    difficulty: str
    title: str
    slides: List[SlideData]
    quiz: List[QuizData]

class LectureList(BaseModel):
    lectures: List[LectureData]
