import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM

from app.core.database import Base


class InterviewStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class InterviewType(str, enum.Enum):
    online = "online"
    offline = "offline"


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)

    scheduled_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=True)
    interview_type = Column(ENUM('online', 'offline', name='interview_type', create_type=False), nullable=False)
    location = Column(String(500), nullable=True)
    online_link = Column(String(1000), nullable=True)

    status = Column(ENUM('scheduled', 'completed', 'cancelled', name='interview_status', create_type=False), nullable=False, default="scheduled")

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    candidate = relationship("Candidate", back_populates="interviews")
    interviewers = relationship("InterviewInterviewer", back_populates="interview", cascade="all, delete-orphan")


class InterviewInterviewer(Base):
    __tablename__ = "interview_interviewers"

    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    interview = relationship("Interview", back_populates="interviewers")
    user = relationship("User", back_populates="interview_slots")
