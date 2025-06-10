from pydantic import BaseModel
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
    room: str

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
    required: List[str]
    passmark: int
    room: str

class StepData(BaseModel):
    title: str
    description: str
    code: str
    options: List[str]
    answer: str

class GuidedProjectData(BaseModel):
    name: str
    description: str
    difficulty: str
    steps: List[StepData]
    hints: List[str]
    solution: str
    room: str

class CompletionData(BaseModel):
    lectures: List[str]
    projects: List[str]
    puzzles: List[str]

class UserData(BaseModel):
    username: str
    room: str
    completions: CompletionData
    level: str

class LectureCompletionRequest(BaseModel):
    username: str
    room: str
    lecture: str

class ProjectCompletionRequest(BaseModel):
    username: str
    room: str
    project: str

class PuzzleCompletionRequest(BaseModel):
    username: str
    room: str
    puzzle: str

class CodeRequest(BaseModel):
    code: str

class RoomData(BaseModel):
    owner: str
    name: str
    capacity: int

class TutorRegister(BaseModel):
    username: str
    password: str
    email: str
    type: str
    institution: str

class ChallengeData(BaseModel):
    date: str
    description: str
    name: str
    room: str
    tests: List[str]