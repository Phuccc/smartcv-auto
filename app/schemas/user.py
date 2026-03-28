from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


# ── USER SCHEMAS ────────────────────────────────────────────

class UserBase(BaseModel):
    full_name: str
    email: str
    role: str = "hr_staff"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── ROLE SCHEMAS ─────────────────────────────────────────────

class RolePermissionItem(BaseModel):
    resource: str
    can_create: bool = False
    can_read: bool = False
    can_update: bool = False
    can_delete: bool = False

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str
    display_name: str


class RoleUpdate(BaseModel):
    display_name: Optional[str] = None


class RoleOut(BaseModel):
    name: str
    display_name: str
    is_system: bool

    model_config = {"from_attributes": True}


class RoleDetailOut(RoleOut):
    permissions: List[RolePermissionItem] = []
