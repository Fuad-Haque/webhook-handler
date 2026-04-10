from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import uuid


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_min_length(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class EventLog(BaseModel):
    id: str
    source: str  # stripe / github / shopify
    event_type: str
    received_at: datetime
    processed_at: Optional[datetime] = None
    status: str  # received / processing / complete / ignored / error
    payload: dict
    result: Optional[dict] = None
    error: Optional[str] = None


class DashboardResponse(BaseModel):
    total_events: int
    by_source: dict
    by_status: dict
    recent_events: list
    error_rate: float  # percentage


class EventFilter(BaseModel):
    source: Optional[str] = None
    status: Optional[str] = None
    event_type: Optional[str] = None