from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from app.models.candidate import GenderType, ApplicationStatus


# ── LINKS ────────────────────────────────────────────────────────────────────

class CandidateLinkBase(BaseModel):
    label: str
    url: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"label": "GitHub", "url": "https://github.com/nguyenvana"}]
        }
    }


class CandidateLinkUpdate(BaseModel):
    label: Optional[str] = None
    url: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"label": "LinkedIn", "url": "https://linkedin.com/in/nguyenvana"}]
        }
    }


class CandidateLinkOut(CandidateLinkBase):
    id: int
    model_config = {"from_attributes": True}


# ── EDUCATION ────────────────────────────────────────────────────────────────

class CandidateEducationBase(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    major: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "degree": "Cử nhân",
                "institution": "Đại học Bách Khoa HCM",
                "major": "Công nghệ thông tin",
                "start_year": 2017,
                "end_year": 2021
            }]
        }
    }


class CandidateEducationUpdate(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    major: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"major": "Khoa học máy tính", "end_year": 2022}]
        }
    }


class CandidateEducationOut(CandidateEducationBase):
    id: int
    model_config = {"from_attributes": True}


# ── EXPERIENCE ───────────────────────────────────────────────────────────────

class CandidateExperienceBase(BaseModel):
    company_name: str
    position: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "company_name": "Công ty Tech ABC",
                "position": "Backend Developer",
                "start_date": "2021-05-01",
                "end_date": "2023-12-31",
                "description": "Xây dựng hệ thống API bằng FastAPI và PostgreSQL, quản lý team 3 người."
            }]
        }
    }


class CandidateExperienceUpdate(BaseModel):
    company_name: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"end_date": "2024-03-31", "description": "Cập nhật mô tả công việc."}]
        }
    }


class CandidateExperienceOut(CandidateExperienceBase):
    id: int
    model_config = {"from_attributes": True}


# ── NOTES ────────────────────────────────────────────────────────────────────

class CandidateNoteCreate(BaseModel):
    content: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"content": "Ứng viên có thái độ tốt, cần phỏng vấn thêm về technical."}]
        }
    }


class CandidateNoteUpdate(BaseModel):
    content: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"content": "Đã phỏng vấn kỹ thuật, đánh giá tốt. Chuyển sang vòng offer."}]
        }
    }


class CandidateNoteOut(BaseModel):
    id: int
    content: str
    created_by: int
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── CREATE / UPDATE / OUT ─────────────────────────────────────────────────────

class CandidateCreate(BaseModel):
    full_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[GenderType] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    specific_address: Optional[str] = None
    job_id: Optional[int] = None
    status: ApplicationStatus = ApplicationStatus.new
    applied_date: Optional[date] = None
    assigned_to: Optional[int] = None
    score: Optional[float] = None
    ai_summary: Optional[str] = None
    education: Optional[List[CandidateEducationBase]] = []
    experience: Optional[List[CandidateExperienceBase]] = []
    skill_ids: Optional[List[int]] = []
    facebook: Optional[str] = None
    cv_link: Optional[str] = None
    portfolio_link: Optional[str] = None
    links: Optional[List[CandidateLinkBase]] = []

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "full_name": "Nguyễn Văn A",
                "date_of_birth": "1998-05-15",
                "gender": "male",
                "phone": "0901234567",
                "email": "nguyen.a@example.com",
                "specific_address": "123 Nguyễn Trãi, Q.1",
                "job_id": 1,
                "status": "mới",
                "applied_date": "2026-03-10",
                "assigned_to": 1,
                "score": 8.5,
                "ai_summary": "Ứng viên tiềm năng với kinh nghiệm Backend.",
                "education": [
                    {
                        "degree": "Cử nhân",
                        "institution": "Đại học Bách Khoa HCM",
                        "major": "Công nghệ thông tin",
                        "start_year": 2017,
                        "end_year": 2021
                    }
                ],
                "experience": [
                    {
                        "company_name": "Công ty Tech ABC",
                        "position": "Backend Developer",
                        "start_date": "2021-05-01",
                        "end_date": "2023-12-31",
                        "description": "Xây dựng hệ thống API bằng FastAPI và PostgreSQL."
                    }
                ],
                "skill_ids": [1, 2],
                "facebook": "https://facebook.com/nguyenvana",
                "cv_link": "https://drive.google.com/file/d/abc123",
                "portfolio_link": "https://nguyenvana.me",
                "links": [
                    {"label": "GitHub", "url": "https://github.com/nguyenvana"},
                    {"label": "LinkedIn", "url": "https://linkedin.com/in/nguyenvana"}
                ]
            }]
        }
    }


class CandidateUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[GenderType] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    specific_address: Optional[str] = None
    job_id: Optional[int] = None
    status: Optional[ApplicationStatus] = None
    assigned_to: Optional[int] = None
    score: Optional[float] = None
    ai_summary: Optional[str] = None
    facebook: Optional[str] = None
    cv_link: Optional[str] = None
    portfolio_link: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "full_name": "Nguyễn Văn A (Updated)",
                "status": "phỏng vấn", 
                "score": 8.5, 
                "assigned_to": 2
            }]
        }
    }


class CandidateOut(BaseModel):
    id: int
    full_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    specific_address: Optional[str] = None
    job_id: Optional[int] = None
    status: str
    applied_date: Optional[date] = None
    assigned_to: Optional[int] = None
    score: Optional[float] = None
    ai_summary: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    education: List[CandidateEducationOut] = []
    experience: List[CandidateExperienceOut] = []
    notes: List[CandidateNoteOut] = []
    facebook: Optional[str] = None
    cv_link: Optional[str] = None
    portfolio_link: Optional[str] = None
    links: List[CandidateLinkOut] = []
    model_config = {"from_attributes": True}


class CandidateListItem(BaseModel):
    id: int
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    status: str
    job_id: Optional[int] = None
    score: Optional[float] = None
    applied_date: Optional[date] = None
    model_config = {"from_attributes": True}
