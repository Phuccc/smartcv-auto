from pydantic import BaseModel
from typing import Optional

class SystemSettingOut(BaseModel):
    key: str
    value: str

    model_config = {"from_attributes": True}

class SystemSettingUpdate(BaseModel):
    value: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"value": "new_value"}]
        }
    }
