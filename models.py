from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, Text, Float
from sqlalchemy.orm import declarative_base, relationship
from enum import Enum as PyEnum
from datetime import datetime

Base = declarative_base()


class UserRoles(PyEnum):
    user = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRoles), default=UserRoles.user)
    user_img = Column(String, nullable=True)
    places = relationship("Place", back_populates="user")
    comments = relationship("Comment", back_populates="user")


class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    img = Column(String)
    title = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="places")
    user_full_name = Column(String)  # Add user full name
    posted_date = Column(DateTime, default=datetime.utcnow)  # Add posted date
    content = Column(String)
    rating_score = Column(Float)
    tags = Column(String)
    comments = relationship("Comment", back_populates="place")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    place_id = Column(Integer, ForeignKey("places.id"))
    commented_at = Column(DateTime, default=datetime.utcnow)
    comment_text = Column(Text)
    email = Column(String)  # extra add field
    name = Column(String)  # extra add field
    user = relationship("User", back_populates="comments")
    place = relationship("Place", back_populates="comments")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    image = Column(String)  # category related image
    title = Column(String)
    description = Column(String)
