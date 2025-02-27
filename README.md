# BScAppBackend - FastAPI with MongoDB

A simple backend service for user registration, login, and email verification built with **FastAPI** and **MongoDB**.

## Features

- User registration with email, username, and password.
- Email verification with a unique token.
- Secure login with password hashing using bcrypt.

## Setup

1. Clone the repo:
   `git clone https://github.com/denisghera/BScAppBackend.git`
   
2. Set up a virtual environment:
   - `python -m venv venv`
   - `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (macOS/Linux)

3. Install dependencies: `pip install -r requirements.txt`

4. Set up environment variables in a `.env` file:
   - `MONGO_URI=mongodb+srv://<your-mongo-uri>`
   - `MAIL_USERNAME=<your-email-address>`
   - `MAIL_PASSWORD=<your-email-password>`

5. Run the server: `uvicorn main:app --reload`

6. Access the API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
