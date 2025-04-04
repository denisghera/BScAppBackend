from pydantic import BaseModel
from typing import List

class UserRegister(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UsernameRequest(BaseModel):
    username: str
    
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
    required: List[str]
    passmark: int

class LectureList(BaseModel):
    lectures: List[LectureData]

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

class GuidedProjectList(BaseModel):
    guidedProjects: List[GuidedProjectData]

class CompletionData(BaseModel):
    lectures: List[str]
    projects: List[str]
    puzzles: List[str]

class UserData(BaseModel):
    username: str
    completions: CompletionData

class LectureCompletionRequest(BaseModel):
    username: str
    lecture: str

class ProjectCompletionRequest(BaseModel):
    username: str
    project: str

class PuzzleCompletionRequest(BaseModel):
    username: str
    puzzle: str

class CodeRequest(BaseModel):
    code: str