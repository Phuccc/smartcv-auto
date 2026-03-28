from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.models.interview import InterviewStatus, InterviewType


class InterviewCreate(BaseModel):
    candidate_id: int
    scheduled_at: datetime
    interview_type: InterviewType
    location: Optional[str] = None
    online_link: Optional[str] = None
    interviewer_ids: Optional[List[int]] = []


class InterviewUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    interview_type: Optional[InterviewType] = None
    location: Optional[str] = None
    online_link: Optional[str] = None
    status: Optional[InterviewStatus] = None
    interviewer_ids: Optional[List[int]] = None


class InterviewerOut(BaseModel):
    user_id: int
    model_config = {"from_attributes": True}


class InterviewOut(BaseModel):
    id: int
    candidate_id: int
    scheduled_at: datetime
    interview_type: InterviewType
    location: Optional[str] = None
    online_link: Optional[str] = None
    status: InterviewStatus
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    interviewer_ids: List[int] = []

    model_config = {"from_attributes": True}
