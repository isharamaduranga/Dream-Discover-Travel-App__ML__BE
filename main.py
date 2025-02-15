import os
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, File, Form, HTTPException
from starlette.middleware.cors import CORSMiddleware
from typing import List
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crud import create_user, authenticate_user, get_users, get_user, delete_user_from_db, create_place, \
    get_places_by_user_id, get_place_by_place_id, create_comment, get_comments_by_user_id, get_comments_by_place_id, \
    get_all_places_with_comments, get_all_places_with_comments_by_place_id, get_places_by_tag, \
    get_all_places_with_comments_by_search_text, create_travel_plan, update_travel_plan, get_filtered_travel_plans, \
    get_place_sentiment_by_date_range, get_all_categories, get_places_by_category, get_pending_and_inactive_places
from response import create_response
from schemas import User, UserLogin, PlaceCreate, PlaceResponse, PlaceGetByUserId, PlaceGetByPlaceId, CommentCreate, \
    CommentByUserIdResponse, CommentByPlaceIdResponse, TravelPlanCreate


from database import SessionLocal, engine
from models import Base
Base.metadata.create_all(bind=engine)
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
def get_db():
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
            "userRole": user.role
        }
        return create_response("success", "Successfully login", data=user_data)
    else:
        return create_response("error", "Invalid Credential!", data=None)


# API to get all users
@app.get("/api/v1/users", response_model=list[User])
def get_all_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_users(db, skip=skip, limit=limit)

#===================================================
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

        return create_response("success", "Your new place request has been sent for admin approval", data=place)

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


# API to get a place by place ID
@app.post("/api/v1/places/getByPlaceId", response_model=PlaceResponse)
def get_place_by_place_id_endpoint(place_data: PlaceGetByPlaceId, db: Session = Depends(get_db)):
    place = get_place_by_place_id(db, place_id=place_data.place_id)

    # Convert tags from comma-separated string to list
    if place:
        place.tags = place.tags.split(',')

    return place


# Api to create new comment related place
@app.post("/api/v1/createComment")
def create_comment_endpoint(comment: CommentCreate, db: Session = Depends(get_db)):
    try:
        new_comment = create_comment(db, comment)
        return create_response("success", "Comment created successfully", data={"comment_id": new_comment})
    except Exception as e:
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)


# API to get comments by userId in related user
@app.get("/api/v1/getCommentsByUserId/{user_id}", response_model=List[CommentByUserIdResponse])
def get_comments_by_user_id_endpoint(user_id: int, db: Session = Depends(get_db)):
    comments = get_comments_by_user_id(db, user_id)

    # Map the results to CommentByUserIdResponse
    comments_response = [
        CommentByUserIdResponse(
            comment_id=comment.id,
            comment_text=comment.comment_text,
            email=comment.email,
            name=comment.name,
            commented_at=comment.commented_at,
            user_id=comment.user_id,
            place_id=comment.place_id
        )
        for comment in comments
    ]

    return comments_response

# API to get comments by placeId in related place
@app.get("/api/v1/getCommentsByPlaceId/{place_id}", response_model=List[CommentByPlaceIdResponse])
def get_comments_by_place_id_endpoint(place_id: int, db: Session = Depends(get_db)):
    comments = get_comments_by_place_id(db, place_id)
    # Map the results to CommentByUserIdResponse
    comments_response = [
        CommentByUserIdResponse(
            comment_id=comment.id,
            comment_text=comment.comment_text,
            email=comment.email,
            name=comment.name,
            commented_at=comment.commented_at,
            user_id=comment.user_id,
            place_id=comment.place_id
        )
        for comment in comments
    ]

    return comments_response


# API to get all places with comments
@app.get("/api/v1/placesWithComments", response_model=dict)
def get_all_places_with_comments_endpoint(db: Session = Depends(get_db)):
    try:
        places_with_comments = get_all_places_with_comments(db)
        response_data = {
            "status": "success",
            "message": "Successfully fetched",
            "data": {"data": places_with_comments}
        }
        return response_data
    except Exception as e:
        # Handle any exceptions and return an error response
        error_message = "Failed to fetch data. Reason: {}".format(str(e))
        raise HTTPException(status_code=500, detail=error_message)


# API to get all places with comments by place id
@app.get("/api/v1/placesWithComments/{place_id}", response_model=dict)
def get_all_places_with_comments_by_id_endpoint(place_id: int, db: Session = Depends(get_db)):
    try:
        places_with_comments = get_all_places_with_comments_by_place_id(db, place_id)
        response_data = {
            "status": "success",
            "message": "Successfully fetched",
            "data": {"data": places_with_comments}
        }
        return response_data
    except Exception as e:
        # Handle any exceptions and return an error response
        error_message = "Failed to fetch data. Reason: {}".format(str(e))
        raise HTTPException(status_code=500, detail=error_message)


# API to get places by tag
@app.post("/api/v1/places/getByPlace", response_model=dict)
def get_places_by_tag_endpoint(tag: str = Form(...), minscore: float = Form(...), maxscore: float = Form(...),
                               db: Session = Depends(get_db)):
    try:
        places_with_comments = get_places_by_tag(db, tag=tag, min=minscore, max=maxscore)
        response_data = {
            "status": "success",
            "message": "Successfully fetched",
            "data": {"data": places_with_comments}
        }
        return response_data
    except Exception as e:
        error_message = "Failed to fetch data. Reason: {}".format(str(e))
        raise HTTPException(status_code=500, detail=error_message)

# Add a new API endpoint for searching places and comments
@app.get("/api/v1/placesWithComments/search/{search_text}", response_model=dict)
def search_places_and_comments(search_text: str, db: Session = Depends(get_db)
                               ):
    try:
        places_with_comments = get_all_places_with_comments_by_search_text(db, search_text)
        response_data = {
            "status": "success",
            "message": "Successfully fetched",
            "data": {"data": places_with_comments}
        }
        return response_data
    except Exception as e:
        # Handle any exceptions and return an error response
        error_message = f"Failed to fetch data. Reason: {str(e)}"
        raise HTTPException(status_code=500, detail=error_message)


def create_response(status, message, data):
    return {"status": status, "message": message, "data": data}


# this place has before rating system through huggingface inbuilt model now that api change for that comment read
# prediction pypeline through update related place rating score 0 1 or 2 its mean negative , natural or positive

@app.post("/api/v1/places/scoreAndUpdate/{place_id}")
def score_and_update_place(
        place_id: int, db: Session = Depends(get_db)
):
    try:
        # Fetch comments from the database based on place_id
        comments = get_comments_by_place_id(db, place_id)

        # Extract comment text from each comment
        comments_list = [comment.comment_text for comment in comments]

        print("comments", comments_list)

        # Use your machine learning model to score the comments
        scores = [predict_score(comment) for comment in comments_list]

        print("scores total ---> ", scores)
        print("sum of score ---> ", sum(scores))
        print("length of score ---> ", len(scores))

        # Calculate the average score
        avg_score = sum(scores) / len(scores)
        print("avg of score ---> ", avg_score )

        # Update the place rating_score in the database
        place = get_place_by_place_id(db, place_id)
        if place:
            place.rating_score = avg_score
            db.commit()
            db.refresh(place)
            return {"rating_score": avg_score}
        else:
            return create_response("error", "Place not found !", data=None)

    except Exception as e:
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)

# API to get places by tag
@app.patch("/api/v1/places/change-status", response_model=dict)
def change_place_status(request: dict, db: Session = Depends(get_db)):
    try:
        place_id = request.get("place_id")
        status = request.get("status")
        
        if not place_id or not status:
            raise HTTPException(status_code=400, detail="Missing required fields")
            
        place = get_place_by_place_id(db, place_id)
        if not place:
            raise HTTPException(status_code=404, detail="Place not found")
            
        place.status = status
        db.commit()
        db.refresh(place)
        
        return {
            "status": "success", 
            "message": "Status updated successfully"
        }
    except Exception as e:
        error_message = "Failed to update status. Reason: {}".format(str(e))
        raise HTTPException(status_code=500, detail=error_message)

@app.post("/api/v1/travel-plans/")
def create_travel_plan_endpoint(
    user_id: int = Form(...),
    place_id: int = Form(...),
    travel_date: str = Form(...),
    email_address: str = Form(...),
    budget: float = Form(...),
    number_of_travelers: int = Form(...),
    preferred_activities: str = Form(...),
    special_notes: str = Form(None),
    notification_preference: str = Form(...),
    notification_days_before: int = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # Convert string date to datetime
        travel_date = datetime.fromisoformat(travel_date)
        
        travel_plan_data = TravelPlanCreate(
            user_id=user_id,
            place_id=place_id,
            travel_date=travel_date,
            email_address=email_address,
            budget=budget,
            number_of_travelers=number_of_travelers,
            preferred_activities=preferred_activities,
            special_notes=special_notes,
            notification_preference=notification_preference,
            notification_days_before=notification_days_before
        )

        new_travel_plan = create_travel_plan(db, travel_plan_data)
        
        return create_response(
            "success",
            "Travel plan created successfully",
            data={"travel_plan_id": new_travel_plan.id}
        )

    except ValueError as e:
        return create_response("error", f"Invalid data format: {str(e)}", data=None)
    except Exception as e:
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)

@app.put("/api/v1/travel-plans/{travel_plan_id}")
def update_travel_plan_endpoint(
    travel_plan_id: int,
    user_id: int = Form(...),
    place_id: int = Form(...),
    travel_date: str = Form(...),
    email_address: str = Form(...),
    budget: float = Form(...),
    number_of_travelers: int = Form(...),
    preferred_activities: str = Form(...),
    special_notes: str = Form(None),
    notification_preference: str = Form(...),
    notification_days_before: int = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # Convert string date to datetime
        travel_date = datetime.fromisoformat(travel_date)
        
        travel_plan_data = TravelPlanCreate(
            user_id=user_id,
            place_id=place_id,
            travel_date=travel_date,
            email_address=email_address,
            budget=budget,
            number_of_travelers=number_of_travelers,
            preferred_activities=preferred_activities,
            special_notes=special_notes,
            notification_preference=notification_preference,
            notification_days_before=notification_days_before
        )

        updated_travel_plan = update_travel_plan(db, travel_plan_id, travel_plan_data)
        if updated_travel_plan:
            return create_response(
                "success",
                "Travel plan updated successfully",
                data={"travel_plan_id": updated_travel_plan.id}
            )
        return create_response("error", "Travel plan not found", data=None)

    except ValueError as e:
        return create_response("error", f"Invalid data format: {str(e)}", data=None)
    except Exception as e:
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)

@app.get("/api/v1/travel-plans")
def get_travel_plans(
    user_id: int = None,
    place_id: int = None,
    db: Session = Depends(get_db)
):
    try:
        travel_plans = get_filtered_travel_plans(db, user_id, place_id)
        return create_response(
            "success",
            "Travel plans retrieved successfully",
            data={"travel_plans": travel_plans}
        )

    except Exception as e:
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)

@app.get("/api/v1/places/{place_id}/sentiment-analysis")
def get_place_sentiment_analysis(
    place_id: int,
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    try:
        # Convert string dates to datetime objects
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        # Get sentiment analysis data
        sentiment_data = get_place_sentiment_by_date_range(db, place_id, start, end)
        
        if not sentiment_data:
            return create_response("error", "Place not found or no data in date range", data=None)
            
        return create_response(
            "success",
            "Sentiment analysis retrieved successfully",
            data=sentiment_data
        )

    except ValueError as e:
        return create_response("error", f"Invalid date format: {str(e)}", data=None)
    except Exception as e:
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)

@app.get("/api/v1/categories")
def get_categories(db: Session = Depends(get_db)):
    try:
        categories = get_all_categories(db)
        return create_response(
            "success",
            "Categories retrieved successfully",
            data={"categories": categories}
        )
    except Exception as e:
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)

@app.get("/api/v1/categories/{category_id}/places")
def get_places_by_category_id(
    category_id: int,
    db: Session = Depends(get_db)
):
    try:
        places = get_places_by_category(db, category_id)
        if places is None:
            return create_response("error", "Category not found", data=None)
            
        return create_response(
            "success",
            "Places retrieved successfully",
            data={"places": places}
        )

    except Exception as e:
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)

@app.get("/api/v1/places/pending-inactive")
def get_pending_and_inactive_places_endpoint(db: Session = Depends(get_db)):
    try:
        places = get_pending_and_inactive_places(db)
        return create_response(
            "success",
            "Places retrieved successfully",
            data=places
        )
    except Exception as e:
        return create_response("error", f"Internal Server Error: {str(e)}", data=None)
