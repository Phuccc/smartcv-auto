import enum
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Text,
    ForeignKey, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from sqlalchemy.dialects.postgresql import ENUM


class GenderType(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class ApplicationStatus(str, enum.Enum):
    new = "mới"
    approved = "duyệt"
    rejected = "từ chối"
    interviewing = "phỏng vấn"
    offer_sent = "gửi offer"
    hired = "đã tuyển"


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)

    # Thông tin cá nhân
    full_name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(ENUM(GenderType, name="gender_type", create_type=False), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    facebook = Column(String(255), nullable=True)

    # Địa chỉ
    specific_address = Column(String(500), nullable=True)

    # Hồ sơ ứng tuyển
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    cv_link = Column(String(500), nullable=True)
    portfolio_link = Column(String(500), nullable=True)

    # Đánh giá
    ai_summary = Column(Text, nullable=True)
    score = Column(Numeric(4, 2), nullable=True)
    status = Column(ENUM("mới", "duyệt", "từ chối", "phỏng vấn", "gửi offer", "đã tuyển", name="application_status", create_type=False), nullable=False, default="mới")
    applied_date = Column(Date, server_default=func.current_date())

    # Audit
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    job = relationship("Job", back_populates="candidates")
    assigned_user = relationship("User", foreign_keys=[assigned_to], back_populates="candidates_assigned")
    created_user = relationship("User", foreign_keys=[created_by], back_populates="candidates_created")
    links = relationship("CandidateLink", back_populates="candidate", cascade="all, delete-orphan")
    education = relationship("CandidateEducation", back_populates="candidate", cascade="all, delete-orphan")
    experience = relationship("CandidateExperience", back_populates="candidate", cascade="all, delete-orphan")
    skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    notes = relationship("CandidateNote", back_populates="candidate", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")


class CandidateLink(Base):
    __tablename__ = "candidate_links"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    candidate = relationship("Candidate", back_populates="links")


class CandidateEducation(Base):
    __tablename__ = "candidate_education"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    degree = Column(String(100), nullable=True)
    institution = Column(String(255), nullable=True)
    major = Column(String(255), nullable=True)
    start_year = Column(Integer, nullable=True)
    end_year = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    candidate = relationship("Candidate", back_populates="education")


class CandidateExperience(Base):
    __tablename__ = "candidate_experience"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=False)
    position = Column(String(255), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    candidate = relationship("Candidate", back_populates="experience")


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)

    candidate = relationship("Candidate", back_populates="skills")
    skill = relationship("Skill", back_populates="candidate_skills")


class CandidateNote(Base):
    __tablename__ = "candidate_notes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    candidate = relationship("Candidate", back_populates="notes")
    author = relationship("User", back_populates="notes")
