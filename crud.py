# crud.py
import os

import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from fastapi import UploadFile, Form
from passlib.context import CryptContext
from sqlalchemy import desc, and_
from sqlalchemy.orm import Session

from models import UserRoles, User
from response import create_response

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