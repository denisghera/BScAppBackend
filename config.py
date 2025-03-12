from pymongo import MongoClient
from pymongo.collection import Collection
from dotenv import load_dotenv
import os
from fastapi_mail import ConnectionConfig

load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["test_db"]
users_collection: Collection = db["user_credentials"]
daily_puzzle_collection: Collection = db["daily_puzzles"]
user_file_collection: Collection = db["user_files"]
lecture_collection: Collection = db["lectures"]
guided_projects_collection: Collection = db["guided_projects"]
user_data_collection: Collection = db["user_data"]
test_collection: Collection = db["test_collection"]

# Email Configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)
