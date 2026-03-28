import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from sqlalchemy.dialects.postgresql import ENUM


class JobStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    paused = "paused"


class ExperienceLevel(str, enum.Enum):
    intern = "intern"
    fresher = "fresher"
    junior = "junior"
    mid = "mid"
    senior = "senior"
    lead = "lead"
    manager = "manager"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    experience_level = Column(ENUM("intern", "fresher", "junior", "mid", "senior", "lead", "manager", name="experience_level", create_type=False), nullable=True)
    education_level = Column(String(100), nullable=True)
    quantity = Column(Integer, default=1)

    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    benefits = Column(Text, nullable=True)

    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(10), default="VND")

    status = Column(ENUM("open", "closed", "paused", name="job_status", create_type=False), nullable=False, default="open")

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    department = relationship("Department", back_populates="jobs")
    branch = relationship("Branch", back_populates="jobs")
    candidates = relationship("Candidate", back_populates="job")
    skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")


class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)

    job = relationship("Job", back_populates="skills")
    skill = relationship("Skill", back_populates="job_skills")
