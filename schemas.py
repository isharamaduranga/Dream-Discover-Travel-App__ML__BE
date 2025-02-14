from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from models import NotificationPreference

# user base schemas
class UserBase(BaseModel):
    username: str
    email: str


class User(UserBase):
    id: int
    user_img: str

    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    username: str
    password: str


# place base schemas
class PlaceBase(BaseModel):
    title: str
    content: str
    tags: List[str]
    user_id: int
    user_full_name: str
    rating_score: float


class PlaceCreate(PlaceBase):
    pass


class PlaceResponse(BaseModel):
    id: int
    img: str  # Change the type to str for URLs
    title: str
    content: str
    tags: List[str]
    user_id: int
    user_full_name: str
    rating_score: float
    posted_date: datetime

    class Config:
        orm_mode = True


class PlaceGetByUserId(BaseModel):
    user_id: int


class PlaceGetByPlaceId(BaseModel):
    place_id: int


# comment base schemas
class CommentBase(BaseModel):
    comment_text: str
    email: str
    name: str
    static_rating: float

class CommentCreate(CommentBase):
    place_id: int
    user_id: int


class CommentByUserIdResponse(BaseModel):
    comment_id: int
    comment_text: str
    email: str
    name: str
    commented_at: datetime
    user_id: int
    place_id: int


class CommentByPlaceIdResponse(BaseModel):
    comment_id: int
    comment_text: str
    email: str
    name: str
    commented_at: datetime
    user_id: int
    place_id: int


class CommentResponse(BaseModel):
    comment_id: int
    comment_text: str
    email: str
    name: str
    commented_at: datetime
    user_id: int
    user_image: str
    place_id: int
    static_rating: float = 0.0  # Default value
    label: str = "neutral"  # Default value


class TravelPlanCreate(BaseModel):
    user_id: int
    place_id: int
    travel_date: datetime
    email_address: str
    budget: float
    number_of_travelers: int
    preferred_activities: str
    special_notes: Optional[str] = None
    notification_preference: NotificationPreference
    notification_days_before: Optional[int] = None

class TravelPlanResponse(TravelPlanCreate):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True