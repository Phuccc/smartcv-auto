from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.database import get_db
from app.deps import require_permission
from app.models.job import Job, JobSkill
from app.models.department import Branch
from app.models.user import User
from app.schemas.job import JobCreate, JobUpdate, JobOut, JobListItem
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

_SORTABLE_FIELDS = {
    "title":      Job.title,
    "status":     Job.status,
    "quantity":   Job.quantity,
    "created_at": Job.created_at,
}


def _job_to_out(job: Job) -> dict:
    data = {c.key: getattr(job, c.key) for c in job.__mapper__.columns}
    data["skill_ids"] = [js.skill_id for js in job.skills] if job.skills else []
    data["branch_name"] = job.branch.name if job.branch else None
    return data


def _job_to_list_item(job: Job) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "department_id": job.department_id,
        "branch_id": job.branch_id,
        "branch_name": job.branch.name if job.branch else None,
        "experience_level": job.experience_level,
        "education_level": job.education_level,
        "quantity": job.quantity,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "status": job.status,
    }


def _job_options():
    return [selectinload(Job.skills), selectinload(Job.branch)]


@router.get("", response_model=PaginatedResponse[JobListItem],
            summary="Danh sách vị trí tuyển dụng")
async def list_jobs(
    # ── Filters ────────────────────────────────────────────
    status:        Optional[str] = Query(None, description="Lọc theo trạng thái: open | closed | paused"),
    department_id: Optional[int] = Query(None, description="Lọc theo phòng ban"),
    branch_id:     Optional[int] = Query(None, description="Lọc theo chi nhánh ID"),
    branch_name:   Optional[str] = Query(None, description="Lọc theo tên chi nhánh"),
    experience_level: Optional[str] = Query(None, description="Lọc theo kinh nghiệm: intern | fresher | junior | mid | senior | lead | manager"),
    q:             Optional[str] = Query(None, description="Tìm kiếm theo tên vị trí"),
    # ── Sorting ─────────────────────────────────────────────
    sort_by:    str = Query("created_at", description="Trường sắp xếp: title | status | quantity | created_at"),
    sort_order: str = Query("desc",       description="asc | desc"),
    # ── Pagination ──────────────────────────────────────────
    page: int        = Query(1,  ge=1,        description="Trang hiện tại"),
    size: int        = Query(20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    db: AsyncSession = Depends(get_db),
    _: User          = Depends(require_permission("jobs", "read")),
):
    query = select(Job).options(*_job_options())

    if status:
        query = query.where(Job.status == status)
    if department_id:
        query = query.where(Job.department_id == department_id)
    if branch_id:
        query = query.where(Job.branch_id == branch_id)
    if branch_name:
        query = query.join(Branch).where(Branch.name.ilike(f"%{branch_name.strip()}%"))
    if experience_level:
        query = query.where(Job.experience_level == experience_level)
    if q:
        query = query.where(Job.title.ilike(f"%{q.strip()}%"))

    # Count (không load relations)
    count_stmt = select(func.count(Job.id))
    if branch_name:
        count_stmt = count_stmt.join(Branch)
    
    if status:
        count_stmt = count_stmt.where(Job.status == status)
    if department_id:
        count_stmt = count_stmt.where(Job.department_id == department_id)
    if branch_id:
        count_stmt = count_stmt.where(Job.branch_id == branch_id)
    if branch_name:
        count_stmt = count_stmt.where(Branch.name.ilike(f"%{branch_name.strip()}%"))
    if experience_level:
        count_stmt = count_stmt.where(Job.experience_level == experience_level)
    if q:
        count_stmt = count_stmt.where(Job.title.ilike(f"%{q.strip()}%"))

    total = (await db.execute(count_stmt)).scalar() or 0

    sort_col = _SORTABLE_FIELDS.get(sort_by, Job.created_at)
    query = query.order_by(sort_col.asc() if sort_order.lower() == "asc" else sort_col.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    items = [_job_to_list_item(j) for j in result.scalars().all()]
    return PaginatedResponse(total=total, page=page, size=size, items=items)


@router.post("", response_model=JobOut, status_code=201, summary="Tạo vị trí tuyển dụng mới")
async def create_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("jobs", "create")),
):
    job = Job(
        title=body.title,
        department_id=body.department_id,
        branch_id=body.branch_id,
        experience_level=body.experience_level,
        education_level=body.education_level,
        quantity=body.quantity,
        description=body.description,
        requirements=body.requirements,
        benefits=body.benefits,
        salary_min=body.salary_min,
        salary_max=body.salary_max,
        salary_currency=body.salary_currency,
        status=body.status,
        created_by=current_user.id,
    )
    db.add(job)
    await db.flush()

    for skill_id in (body.skill_ids or []):
        db.add(JobSkill(job_id=job.id, skill_id=skill_id))

    await db.commit()
    result = await db.execute(
        select(Job).options(*_job_options()).where(Job.id == job.id)
    )
    return _job_to_out(result.scalar_one())


@router.get("/{job_id}", response_model=JobOut, summary="Chi tiết vị trí tuyển dụng")
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("jobs", "read")),
):
    result = await db.execute(
        select(Job).options(*_job_options()).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")
    return _job_to_out(job)


@router.post("/{job_id}/update", response_model=JobOut, summary="Cập nhật vị trí tuyển dụng")
async def update_job(
    job_id: int,
    body: JobUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("jobs", "update")),
):
    result = await db.execute(
        select(Job).options(*_job_options()).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")

    updates = body.model_dump(exclude_unset=True)
    skill_ids = updates.pop("skill_ids", None)

    for field, val in updates.items():
        setattr(job, field, val)

    if skill_ids is not None:
        await db.execute(JobSkill.__table__.delete().where(JobSkill.job_id == job_id))
        for skill_id in skill_ids:
            db.add(JobSkill(job_id=job.id, skill_id=skill_id))

    await db.commit()
    result2 = await db.execute(
        select(Job).options(*_job_options()).where(Job.id == job_id)
    )
    return _job_to_out(result2.scalar_one())


@router.delete("/{job_id}", status_code=204, summary="Xóa vị trí tuyển dụng (hard delete)")
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("jobs", "delete")),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")
    await db.delete(job)
    await db.commit()
