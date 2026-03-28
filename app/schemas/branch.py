from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class BranchCreate(BaseModel):
    name: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"name": "Hà Nội"}]
        }
    }


class BranchUpdate(BaseModel):
    name: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"name": "Hồ Chí Minh"}]
        }
    }


class BranchOut(BaseModel):
    id: int
    name: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
