from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.deps import require_permission
from app.models.department import Department, Skill
from app.models.user import User
from app.schemas.department import (
    DepartmentCreate, DepartmentUpdate, DepartmentOut,
    SkillCreate, SkillUpdate, SkillOut,
)

depts_router  = APIRouter(prefix="/departments", tags=["departments"])
skills_router = APIRouter(prefix="/skills",      tags=["skills"])


# ──────────────────────── DEPARTMENTS ────────────────────────

@depts_router.get("", response_model=List[DepartmentOut])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("departments", "read")),
):
    result = await db.execute(select(Department).order_by(Department.id))
    return result.scalars().all()


@depts_router.post("", response_model=DepartmentOut, status_code=201)
async def create_department(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("departments", "create")),
):
    dept = Department(name=body.name)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@depts_router.get("/{dept_id}", response_model=DepartmentOut)
async def get_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("departments", "read")),
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng ban")
    return dept


@depts_router.post("/{dept_id}/update", response_model=DepartmentOut)
async def update_department(
    dept_id: int,
    body: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("departments", "update")),
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng ban")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(dept, field, val)
    await db.commit()
    await db.refresh(dept)
    return dept


@depts_router.delete("/{dept_id}", status_code=204)
async def delete_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("departments", "delete")),
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng ban")
    await db.delete(dept)
    await db.commit()


# ──────────────────────── SKILLS ────────────────────────────

@skills_router.get("", response_model=List[SkillOut])
async def list_skills(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("skills", "read")),
):
    result = await db.execute(select(Skill).order_by(Skill.name))
    return result.scalars().all()


@skills_router.post("", response_model=SkillOut, status_code=201)
async def create_skill(
    body: SkillCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("skills", "create")),
):
    skill = Skill(name=body.name)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill


@skills_router.get("/{skill_id}", response_model=SkillOut)
async def get_skill(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("skills", "read")),
):
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Không tìm thấy kỹ năng")
    return skill


@skills_router.post("/{skill_id}/update", response_model=SkillOut)
async def update_skill(
    skill_id: int,
    body: SkillUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("skills", "update")),
):
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Không tìm thấy kỹ năng")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(skill, field, val)
    await db.commit()
    await db.refresh(skill)
    return skill


@skills_router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("skills", "delete")),
):
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Không tìm thấy kỹ năng")
    await db.delete(skill)
    await db.commit()
