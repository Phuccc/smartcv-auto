from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class DepartmentBase(BaseModel):
    name: str


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None


class DepartmentOut(DepartmentBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SkillBase(BaseModel):
    name: str


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    name: Optional[str] = None


class SkillOut(SkillBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
