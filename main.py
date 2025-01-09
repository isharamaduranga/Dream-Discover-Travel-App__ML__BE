import os

from fastapi import Depends, FastAPI, File, Form, HTTPException
from starlette.middleware.cors import CORSMiddleware
from typing import List
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crud import create_user, authenticate_user, get_users, get_user, delete_user_from_db, create_place, \
    get_places_by_user_id
from response import create_response
from schemas import User, UserLogin, PlaceCreate, PlaceResponse, PlaceGetByUserId

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


# API to get all users
@app.get("/api/v1/users", response_model=list[User])
def get_all_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_users(db, skip=skip, limit=limit)


# API to get a specific user
@app.get("/api/v1/users/{user_id}")
def get_specific_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user = get_user(db, user_id)
        if user is not None:
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "user_img": user.user_img
            }
            return create_response("success", "User retrieved successfully", data=user_data)
        else:
            return create_response("error", "User not found", data=None)
    except Exception as e:
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)


@app.delete("/api/v1/users/{user_id}")
def delete_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    try:
        deleted_user = delete_user_from_db(db, user_id)
        if deleted_user:
            return create_response("success", "User deleted successfully", data=None)
        else:
            return create_response("error", "User not found", data=None)
    except Exception as e:
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)


# API to create a new place
@app.post("/api/v1/createPlace/")
def create_place_endpoint(
        title: str = Form(...),
        content: str = Form(...),
        tags: str = Form(...),
        user_id: int = Form(...),
        user_full_name: str = Form(...),
        rating_score: float = Form(...),
        img: UploadFile = File(...),
        db: Session = Depends(get_db),
):
    try:
        # Create a new PlaceCreate object
        place_data = PlaceCreate(
            title=title,
            content=content,
            tags=tags.split(','),
            user_id=user_id,
            user_full_name=user_full_name,
            rating_score=rating_score,
        )

        # Create the place in the database
        new_place = create_place(db, place_data, img)

        place = {
            "place_id": new_place.id,
            "user_id": new_place.user_id
        }

        return create_response("success", "Place created successfully", data=place)

    except IntegrityError as e:
        db.rollback()
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)

    except Exception as e:
        db.rollback()
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)


# API to get places by user ID
@app.post("/api/v1/places/getByUserId", response_model=List[PlaceResponse])
def get_places_by_user_id_endpoint(user_data: PlaceGetByUserId, db: Session = Depends(get_db)):
    places = get_places_by_user_id(db, user_id=user_data.user_id)

    # Convert tags from comma-separated string to list
    for place in places:
        place.tags = place.tags.split(',')

    return places



