import os

from fastapi import Depends, FastAPI, File, Form, HTTPException
from starlette.middleware.cors import CORSMiddleware
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crud import create_user, authenticate_user
from response import create_response
from schemas import User, UserLogin
app = FastAPI()

# Enable CORS (Cross-Origin Resource Sharing) for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get the current user from the database
def get_db(SessionLocal=None):
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API to register a new user
@app.post("/api/v1/register")
def register_user(
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        user_img: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    try:
        return create_user(db, username=username, email=email, password=password, user_img=user_img)
    except IntegrityError as e:
        return create_response("error", "Email already registered!", data=None)


# API to login
@app.post("/api/v1/login")
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, username=user_credentials.username, password=user_credentials.password)
    if user:
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
        return create_response("success", "Successfully login", data=user_data)
    else:
        return create_response("error", "Invalid Credential!", data=None)