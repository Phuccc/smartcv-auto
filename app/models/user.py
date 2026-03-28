import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


# Giữ lại enum cho code tương thích (không dùng trong DB nữa)
class UserRole(str, enum.Enum):
    admin = "admin"
    hr_staff = "hr_staff"
    interviewer = "interviewer"


class Role(Base):
    """Bảng danh sách vai trò — hỗ trợ tạo vai trò tùy chỉnh."""
    __tablename__ = "roles"

    name         = Column(String(100), primary_key=True)
    display_name = Column(String(255), nullable=False)
    is_system    = Column(Boolean, default=False)
    created_at   = Column(DateTime, server_default=func.now())

    # Không khai báo Role.users — relationship ngược chiều phức tạp, không cần thiết
    permissions = relationship("RolePermission", back_populates="role_obj",
                                cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    full_name     = Column(String(255), nullable=False)
    email         = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role          = Column(String(100), nullable=False, default="hr_staff",
                           server_default="hr_staff")
    is_active     = Column(Boolean, default=True)
    avatar_url    = Column(String(255), nullable=True)
    api_key       = Column(String(255), unique=True, index=True, nullable=True)
    created_at    = Column(DateTime, server_default=func.now())

    candidates_assigned = relationship("Candidate", foreign_keys="Candidate.assigned_to",
                                       back_populates="assigned_user")
    candidates_created  = relationship("Candidate", foreign_keys="Candidate.created_by",
                                       back_populates="created_user")
    notes               = relationship("CandidateNote", back_populates="author")
    interview_slots     = relationship("InterviewInterviewer", back_populates="user")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role       = Column(String(100),
                        ForeignKey("roles.name", ondelete="CASCADE", onupdate="CASCADE"),
                        primary_key=True)
    resource   = Column(String(100), primary_key=True)
    can_create = Column(Boolean, default=False)
    can_read   = Column(Boolean, default=False)
    can_update = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)

    role_obj = relationship("Role", back_populates="permissions")
