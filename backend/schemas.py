from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = True
    chat_mode: str = "free"
    selected_document_ids: Optional[list[int]] = None
    selected_category_id: Optional[int] = None


class DocumentCategoryCreate(BaseModel):
    name: str


class DocumentCategoryUpdate(BaseModel):
    name: str


class ClearHistoryRequest(BaseModel):
    session_id: Optional[str] = None


class AIConfigUpdate(BaseModel):
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class AIConfigResponse(BaseModel):
    model: str
    base_url: Optional[str] = None
    has_api_key: bool  # don't expose the key itself, just whether it's set
