
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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