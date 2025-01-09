# user base schemas
from fastapi import UploadFile, Form
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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