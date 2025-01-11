# crud.py
import os
from datetime import datetime

import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from fastapi import UploadFile, Form
from passlib.context import CryptContext
from sqlalchemy import desc, and_
from sqlalchemy.orm import Session

from models import UserRoles, User, Place, Comment
from response import create_response
from schemas import PlaceCreate, CommentCreate, CommentResponse

# Load environment variables from .env file
load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Function to hash a password
def get_password_hash(password: str):
    return pwd_context.hash(password)

# Common Function to upload images to aws s3 bucket
def upload_to_aws(file, bucket, s3_file, acl="public-read"):
    print(f"Uploading {s3_file} to {bucket}")

    s3 = boto3.client('s3', aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                      aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                      region_name=os.environ.get("REGION_NAME"))
    try:
        # Ensure the file cursor is at the beginning before uploading
        file.seek(0)
        s3.upload_fileobj(file, bucket, s3_file, ExtraArgs={'ACL': acl})
        print("Upload Successful")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False

# Function to create new user and saved
def create_user(
        db: Session,
        username: str,
        email: str,
        password: str,
        user_img: UploadFile = Form(...),
        role: UserRoles = UserRoles.user
):
    hashed_password = get_password_hash(password)

    # Check if user_img is provided
    user_img_url = None
    if user_img:
        # Upload the image to AWS S3 or any other storage
        bucket_name = 'dreamdiscover'
        region_name = '.s3.ap-south-1.amazonaws.com'
        s3_file_path = f"uploads/{user_img.filename}"

        if upload_to_aws(user_img.file, bucket_name, s3_file_path):
            user_img_url = f"https://{bucket_name}{region_name}/{s3_file_path}"

    db_user = User(username=username, email=email, hashed_password=hashed_password, role=role, user_img=user_img_url)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return create_response("success", "User created successfully", data={"user_id": db_user.id})

# Function to get specific user by userId
def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

# Function to get All users from db
def get_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(User).offset(skip).limit(limit).all()

# Function to user authentication
def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.email == username).first()
    if user and pwd_context.verify(password, user.hashed_password):
        return user
    return None

# Function to delete user
def delete_user_from_db(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return user
    else:
        return None

# Function to create new place or location
def create_place(db: Session, place: PlaceCreate, img: UploadFile):
    try:
        # Upload the image to AWS S3
        bucket_name = 'dreamdiscover'
        region_name = '.s3.ap-south-1.amazonaws.com'
        s3_file_path = f"uploads/{img.filename}"

        if upload_to_aws(img.file, bucket_name, s3_file_path):
            # If the upload is successful, create the Place record in the database
            tags_str = ",".join(place.tags)
            place_db = Place(
                img=f"https://{bucket_name}{region_name}/{s3_file_path}",
                title=place.title,
                user_id=place.user_id,
                user_full_name=place.user_full_name,
                posted_date=datetime.utcnow(),
                content=place.content,
                rating_score=place.rating_score,
                tags=tags_str
            )

            db.add(place_db)
            db.commit()
            db.refresh(place_db)

            return place_db
        else:
            # Handle the case when the upload fails
            return create_response("error", "Failed to upload image to S3", data=None)
            # raise HTTPException(status_code=500, detail="Failed to upload image to S3")

    except Exception as e:
        # Handle other exceptions
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)
        # raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Function to get places by userId
def get_places_by_user_id(db: Session, user_id: int):
    return db.query(Place).filter(Place.user_id == user_id).all()

# Function to get places by placeId
def get_place_by_place_id(db: Session, place_id: int):
    return db.query(Place).filter(Place.id == place_id).first()

# Function to create comment
def create_comment(db: Session, comment: CommentCreate):
    db_comment = Comment(
        comment_text=comment.comment_text,
        email=comment.email,
        name=comment.name,
        place_id=comment.place_id,
        user_id=comment.user_id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

# Function to get comments by userId
def get_comments_by_user_id(db: Session, user_id: int):
    return db.query(Comment).filter(Comment.user_id == user_id).all()

# Function to get comments by placeId
def get_comments_by_place_id(db: Session, place_id: int):
    return db.query(Comment).filter(Comment.place_id == place_id).all()

# Function to get All places with comments
def get_all_places_with_comments(db: Session):
    places = db.query(Place).all()
    places_with_comments = []

    for place in places:
        comments = get_comments_by_place_id(db, place.id)
        user = get_user(db, place.user_id)

        comments_response = []

        for comment in comments:
            # Get user information for the comment's user
            comment_user = get_user(db, comment.user_id)

            comment_response = CommentResponse(
                comment_id=comment.id,
                comment_text=comment.comment_text,
                email=comment.email,
                name=comment.name,
                commented_at=comment.commented_at,
                user_id=comment.user_id,
                user_image=comment_user.user_img,  # Set user_image for the comment
                place_id=comment.place_id
            )

            comments_response.append(comment_response)

        place_with_comments = {
            "id": place.id,
            "img": place.img,
            "title": place.title,
            "content": place.content,
            "tags": place.tags.split(','),
            "user_id": place.user_id,
            "user_full_name": place.user_full_name,
            "rating_score": place.rating_score,
            "posted_date": place.posted_date,
            "user_image": user.user_img,
            "comments": comments_response
        }

        places_with_comments.append(place_with_comments)

    return places_with_comments

# Function to get All places with comments by place id
def get_all_places_with_comments_by_place_id(db: Session, place_id: int):
    places = db.query(Place).filter(Place.id == place_id).all()
    places_with_comments_by_id = []

    for place in places:
        comments = get_comments_by_place_id(db, place.id)
        user = get_user(db, place.user_id)

        comments_response = []

        for comment in comments:
            # Get user information for the comment's user
            comment_user = get_user(db, comment.user_id)

            comment_response = CommentResponse(
                comment_id=comment.id,
                comment_text=comment.comment_text,
                email=comment.email,
                name=comment.name,
                commented_at=comment.commented_at,
                user_id=comment.user_id,
                user_image=comment_user.user_img,  # Set user_image for the comment
                place_id=comment.place_id
            )

            comments_response.append(comment_response)

        place_with_comments = {
            "id": place.id,
            "img": place.img,
            "title": place.title,
            "content": place.content,
            "tags": place.tags.split(','),
            "user_id": place.user_id,
            "user_full_name": place.user_full_name,
            "rating_score": place.rating_score,
            "posted_date": place.posted_date,
            "user_image": user.user_img,
            "comments": comments_response
        }

        places_with_comments_by_id.append(place_with_comments)

    return places_with_comments_by_id


# Add a new function to get places by tag
def get_places_by_tag(db: Session, tag: str, min: float, max: float):
    places = db.query(Place).filter(Place.tags.ilike(f"%{tag}%")).filter(and_(Place.rating_score >= min, Place.rating_score <= max)).order_by(desc(Place.rating_score)).all()
    places_with_comments_result = []

    for place in places:
        comments = get_comments_by_place_id(db, place.id)
        user = get_user(db, place.user_id)

        comments_response = []

        for comment in comments:
            # Get user information for the comment's user
            comment_user = get_user(db, comment.user_id)

            comment_response = CommentResponse(
                comment_id=comment.id,
                comment_text=comment.comment_text,
                email=comment.email,
                name=comment.name,
                commented_at=comment.commented_at,
                user_id=comment.user_id,
                user_image=comment_user.user_img,  # Set user_image for the comment
                place_id=comment.place_id
            )

            comments_response.append(comment_response)

        place_with_comments = {
            "id": place.id,
            "img": place.img,
            "title": place.title,
            "content": place.content,
            "tags": place.tags.split(','),
            "user_id": place.user_id,
            "user_full_name": place.user_full_name,
            "rating_score": place.rating_score,
            "posted_date": place.posted_date,
            "user_image": user.user_img,
            "comments": comments_response
        }

        places_with_comments_result.append(place_with_comments)

    return places_with_comments_result


# Add a new function to search for places and comments
def get_all_places_with_comments_by_search_text(db: Session, search_text: str):
    # Perform a case-insensitive search for places and comments where title or tags contain the search text
    places = db.query(Place).filter(
        (Place.title.ilike(f"%{search_text}%")) |
        (Place.tags.ilike(f"%{search_text}%"))
    ).all()

    places_with_comments = []

    for place in places:
        comments = db.query(Comment).filter(Comment.place_id == place.id).all()
        user = get_user(db, place.user_id)

        comments_response = []

        for comment in comments:
            # Get user information for the comment's user
            comment_user = get_user(db, comment.user_id)

            comment_response = CommentResponse(
                comment_id=comment.id,
                comment_text=comment.comment_text,
                email=comment.email,
                name=comment.name,
                commented_at=comment.commented_at,
                user_id=comment.user_id,
                user_image=comment_user.user_img,  # Set user_image for the comment
                place_id=comment.place_id
            )

            comments_response.append(comment_response)

        place_with_comments = {
            "id": place.id,
            "img": place.img,
            "title": place.title,
            "content": place.content,
            "tags": place.tags.split(','),
            "user_id": place.user_id,
            "user_full_name": place.user_full_name,
            "rating_score": place.rating_score,
            "posted_date": place.posted_date,
            "user_image": user.user_img,
            "comments": comments_response
        }

        places_with_comments.append(place_with_comments)

    return places_with_comments



