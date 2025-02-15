# crud.py
import os
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from fastapi import UploadFile, Form
from passlib.context import CryptContext
from sqlalchemy import desc, and_
from sqlalchemy.orm import Session

from models import UserRoles, User, Place, Comment, TravelPlan, PlaceStatus, Category
from response import create_response
from schemas import PlaceCreate, CommentCreate, CommentResponse, TravelPlanCreate
from predictionPipeline import analyze_text

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
    # Get sentiment analysis result
    sentiment = analyze_text(comment.comment_text)
    
    # Get the place from db
    place = db.query(Place).filter(Place.id == comment.place_id).first()

    if not place:
        return None  # Or raise an appropriate exception
    
    # Update sentiment counts based on the analysis result
    if sentiment == 'negative':
        place.negative_count += 1
    elif sentiment == 'positive':
        place.positive_count += 1
    elif sentiment == 'neutral':
        place.neutral_count += 1
    
    db_comment = Comment(
        comment_text=comment.comment_text,
        email=comment.email,
        name=comment.name,
        place_id=comment.place_id,
        user_id=comment.user_id,
        label=sentiment,
        static_rating=comment.static_rating
    )
    
    db.add(db_comment)
    db.commit()  # This commit will save both the comment and place changes
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
    places = db.query(Place).filter(Place.status == PlaceStatus.active).all()
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
                place_id=comment.place_id,
                static_rating=comment.static_rating,
                label=comment.label
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
                place_id=comment.place_id,
                static_rating=comment.static_rating,
                label=comment.label
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
            "negative_sentiment_count": place.negative_count,
            "positive_sentiment_count": place.positive_count,
            "neutral_sentiment_count": place.neutral_count,
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

def create_travel_plan(db: Session, travel_plan: TravelPlanCreate):
    db_travel_plan = TravelPlan(
        user_id=travel_plan.user_id,
        place_id=travel_plan.place_id,
        travel_date=travel_plan.travel_date,
        email_address=travel_plan.email_address,
        budget=travel_plan.budget,
        number_of_travelers=travel_plan.number_of_travelers,
        preferred_activities=travel_plan.preferred_activities,
        special_notes=travel_plan.special_notes,
        notification_preference=travel_plan.notification_preference,
        notification_days_before=travel_plan.notification_days_before
    )
    
    db.add(db_travel_plan)
    db.commit()
    db.refresh(db_travel_plan)
    return db_travel_plan

def update_travel_plan(db: Session, travel_plan_id: int, travel_plan_data: TravelPlanCreate):
    # Get existing travel plan
    db_travel_plan = db.query(TravelPlan).filter(TravelPlan.id == travel_plan_id).first()
    
    if not db_travel_plan:
        return None
        
    # Update travel plan fields
    db_travel_plan.user_id = travel_plan_data.user_id
    db_travel_plan.place_id = travel_plan_data.place_id
    db_travel_plan.travel_date = travel_plan_data.travel_date
    db_travel_plan.email_address = travel_plan_data.email_address
    db_travel_plan.budget = travel_plan_data.budget
    db_travel_plan.number_of_travelers = travel_plan_data.number_of_travelers
    db_travel_plan.preferred_activities = travel_plan_data.preferred_activities
    db_travel_plan.special_notes = travel_plan_data.special_notes
    db_travel_plan.notification_preference = travel_plan_data.notification_preference
    db_travel_plan.notification_days_before = travel_plan_data.notification_days_before
    
    # Save changes
    db.commit()
    db.refresh(db_travel_plan)
    return db_travel_plan

def get_filtered_travel_plans(db: Session, user_id: int = None, place_id: int = None):
    # Start with base query
    query = db.query(TravelPlan)
    
    # Apply filters if provided
    if user_id is not None:
        query = query.filter(TravelPlan.user_id == user_id)
    if place_id is not None:
        query = query.filter(TravelPlan.place_id == place_id)
        
    travel_plans = query.all()
    
    # Convert SQLAlchemy objects to dictionaries with related information
    travel_plans_with_details = []
    for plan in travel_plans:
        place = get_place_by_place_id(db, plan.place_id)
        user = get_user(db, plan.user_id)
        
        plan_dict = {
            "id": plan.id,
            "user_id": plan.user_id,
            "username": user.username if user else None,
            "user_email": user.email if user else None,
            "place_id": plan.place_id,
            "place_title": place.title if place else None,
            "place_img": place.img if place else None,
            "travel_date": plan.travel_date,
            "email_address": plan.email_address,
            "budget": plan.budget,
            "number_of_travelers": plan.number_of_travelers,
            "preferred_activities": plan.preferred_activities,
            "special_notes": plan.special_notes,
            "notification_preference": plan.notification_preference.value,
            "notification_days_before": plan.notification_days_before,
            "created_at": plan.created_at
        }
        travel_plans_with_details.append(plan_dict)
    
    return travel_plans_with_details

def get_place_sentiment_by_date_range(db: Session, place_id: int, start_date: datetime, end_date: datetime):
    # Get the place
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        return None
        
    # Initialize response structure
    response = {
        "place": place.title,
        "date_range": {
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat()
        },
        "tweet_sentiment": []
    }
    
    # Get all comments for this place within the date range
    comments = db.query(Comment).filter(
        Comment.place_id == place_id,
        Comment.commented_at >= start_date,
        Comment.commented_at <= end_date
    ).all()
    
    # Create a dictionary to store counts for each date
    date_sentiments = {}
    current_date = start_date.date()
    
    # Initialize counts for each date in the range
    while current_date <= end_date.date():
        date_sentiments[current_date] = {
            "date": current_date.isoformat(),
            "positive": 0,
            "negative": 0,
            "neutral": 0
        }
        current_date += timedelta(days=1)
    
    # Count sentiments for each comment
    for comment in comments:
        comment_date = comment.commented_at.date()
        if comment.label == "positive":
            date_sentiments[comment_date]["positive"] += 1
        elif comment.label == "negative":
            date_sentiments[comment_date]["negative"] += 1
        elif comment.label == "neutral":
            date_sentiments[comment_date]["neutral"] += 1
    
    # Convert the dictionary to a list sorted by date
    sentiment_list = [
        sentiment_data 
        for date, sentiment_data in sorted(date_sentiments.items())
    ]
    
    response["tweet_sentiment"] = sentiment_list
    return response

def get_all_categories(db: Session):
    categories = db.query(Category).all()
    return [
        {
            "id": category.id,
            "title": category.title
        }
        for category in categories
    ]