from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.models.job import JobStatus, ExperienceLevel


class JobBase(BaseModel):
    title: str
    department_id: Optional[int] = None
    branch_id: Optional[int] = None
    experience_level: Optional[ExperienceLevel] = None
    education_level: Optional[str] = None
    quantity: int = 1
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "VND"
    status: JobStatus = JobStatus.open


class JobCreate(JobBase):
    skill_ids: Optional[List[int]] = []

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "title": "Backend Developer",
                "department_id": 1,
                "branch_id": 1,
                "experience_level": "mid",
                "education_level": "đại học",
                "quantity": 2,
                "description": "Xây dựng API backend cho hệ thống SaaS.",
                "requirements": "• 2+ năm kinh nghiệm Python/FastAPI\n• Thành thạo PostgreSQL",
                "benefits": "• Lương thưởng cạnh tranh\n• 12 ngày phép/năm",
                "salary_min": 20000000,
                "salary_max": 35000000,
                "salary_currency": "VND",
                "status": "open",
                "skill_ids": [4, 7, 8]
            }]
        }
    }


class JobUpdate(BaseModel):
    title: Optional[str] = None
    department_id: Optional[int] = None
    branch_id: Optional[int] = None
    experience_level: Optional[ExperienceLevel] = None
    education_level: Optional[str] = None
    quantity: Optional[int] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    status: Optional[JobStatus] = None
    skill_ids: Optional[List[int]] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"status": "closed", "quantity": 3}]
        }
    }


class JobOut(JobBase):
    id: int
    branch_name: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    skill_ids: List[int] = []

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    id: int
    title: str
    department_id: Optional[int] = None
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    experience_level: Optional[ExperienceLevel] = None
    education_level: Optional[str] = None
    quantity: int = 1
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    status: JobStatus

    model_config = {"from_attributes": True}
