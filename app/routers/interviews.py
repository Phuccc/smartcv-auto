from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.deps import require_permission
from app.models.interview import Interview, InterviewInterviewer
from app.models.user import User
from app.schemas.interview import InterviewCreate, InterviewUpdate, InterviewOut
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/interviews", tags=["interviews"])

_SORTABLE_FIELDS = {
    "scheduled_at": Interview.scheduled_at,
    "status":       Interview.status,
    "created_at":   Interview.created_at,
}


def _to_out(interview: Interview) -> dict:
    data = {c.key: getattr(interview, c.key) for c in interview.__mapper__.columns}
    data["interviewer_ids"] = [ii.user_id for ii in interview.interviewers] if interview.interviewers else []
    return data


def _base_query(current_user: User):
    """Trả về query cơ sở đã apply role-based filter (không load relations)."""
    from sqlalchemy.orm import Query as OrmQuery
    q = select(Interview.id)
    user_role = current_user.role if isinstance(current_user.role, str) else current_user.role.value
    if user_role == "interviewer":
        subq = (
            select(InterviewInterviewer.interview_id)
            .where(InterviewInterviewer.user_id == current_user.id)
            .scalar_subquery()
        )
        q = q.where(Interview.id.in_(subq))
    return q


@router.get("", response_model=PaginatedResponse[InterviewOut])
async def list_interviews(
    # ── Filters ──────────────────────────────────────────────
    candidate_id:    Optional[int]      = Query(None, description="Lọc theo ứng viên"),
    status:          Optional[str]      = Query(None, description="Lọc theo trạng thái phỏng vấn"),
    scheduled_from:  Optional[datetime] = Query(None, description="Lịch phỏng vấn từ ngày"),
    scheduled_to:    Optional[datetime] = Query(None, description="Lịch phỏng vấn đến ngày"),
    # ── Sorting ───────────────────────────────────────────────
    sort_by:    str = Query("scheduled_at", description="Trường sắp xếp: scheduled_at | status | created_at"),
    sort_order: str = Query("desc",         description="asc | desc"),
    # ── Pagination ────────────────────────────────────────────
    page: int        = Query(1,  ge=1,        description="Trang hiện tại"),
    size: int        = Query(20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("interviews", "read")),
):
    # Query chính có load relations
    query = select(Interview).options(selectinload(Interview.interviewers))
    # Query đếm (không load relations, chỉ lấy ID)
    count_query = _base_query(current_user)

    user_role = current_user.role if isinstance(current_user.role, str) else current_user.role.value
    if user_role == "interviewer":
        interviewer_subq = (
            select(InterviewInterviewer.interview_id)
            .where(InterviewInterviewer.user_id == current_user.id)
            .scalar_subquery()
        )
        query = query.where(Interview.id.in_(interviewer_subq))

    # Áp dụng filters cho cả query chính và count_query
    def _apply_filters(q):
        if candidate_id:
            q = q.where(Interview.candidate_id == candidate_id)
        if status:
            q = q.where(Interview.status == status)
        if scheduled_from:
            q = q.where(Interview.scheduled_at >= scheduled_from)
        if scheduled_to:
            q = q.where(Interview.scheduled_at <= scheduled_to)
        return q

    query       = _apply_filters(query)
    count_query = _apply_filters(count_query)

    # Count total
    count_result = await db.execute(select(func.count()).select_from(count_query.subquery()))
    total = count_result.scalar_one()

    # Sorting
    sort_col = _SORTABLE_FIELDS.get(sort_by, Interview.scheduled_at)
    query = query.order_by(sort_col.asc() if sort_order.lower() == "asc" else sort_col.desc())

    # Pagination
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = [_to_out(i) for i in result.scalars().all()]

    return PaginatedResponse(total=total, page=page, size=size, items=items)



@router.post("", response_model=InterviewOut, status_code=201)
async def create_interview(
    body: InterviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("interviews", "create")),
):
    interview = Interview(
        candidate_id=body.candidate_id,
        scheduled_at=body.scheduled_at,
        interview_type=body.interview_type,
        location=body.location,
        online_link=body.online_link,
        created_by=current_user.id,
    )
    db.add(interview)
    await db.flush()

    for user_id in (body.interviewer_ids or []):
        db.add(InterviewInterviewer(interview_id=interview.id, user_id=user_id))

    await db.commit()

    result = await db.execute(
        select(Interview).options(selectinload(Interview.interviewers))
        .where(Interview.id == interview.id)
    )
    return _to_out(result.scalar_one())


@router.get("/{interview_id}", response_model=InterviewOut)
async def get_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("interviews", "read")),
):
    result = await db.execute(
        select(Interview).options(selectinload(Interview.interviewers))
        .where(Interview.id == interview_id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch phỏng vấn")

    # Interviewer chỉ xem lịch của mình
    user_role = current_user.role if isinstance(current_user.role, str) else current_user.role.value
    if user_role == "interviewer":
        ids = [ii.user_id for ii in interview.interviewers]
        if current_user.id not in ids:
            raise HTTPException(status_code=403, detail="Bạn không có quyền xem lịch phỏng vấn này")

    return _to_out(interview)


@router.post("/{interview_id}/update", response_model=InterviewOut)
async def update_interview(
    interview_id: int,
    body: InterviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("interviews", "update")),
):
    result = await db.execute(
        select(Interview).options(selectinload(Interview.interviewers))
        .where(Interview.id == interview_id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch phỏng vấn")

    user_role = current_user.role if isinstance(current_user.role, str) else current_user.role.value
    updates = body.model_dump(exclude_unset=True)

    if user_role == "interviewer":
        # Interviewer không còn được sửa feedback và vote (đã xóa)
        ids = [ii.user_id for ii in interview.interviewers]
        if current_user.id not in ids:
            raise HTTPException(status_code=403, detail="Bạn không có quyền chỉnh sửa lịch này")
        updates = {} # Không cho phép update gì thêm nếu là interviewer đơn thuần? Hoặc giới hạn trường khác.

    # Xử lý interviewer_ids riêng (many-to-many)
    interviewer_ids = updates.pop("interviewer_ids", None)
    for field, val in updates.items():
        setattr(interview, field, val)

    if interviewer_ids is not None and user_role != "interviewer":
        await db.execute(
            InterviewInterviewer.__table__.delete()
            .where(InterviewInterviewer.interview_id == interview_id)
        )
        for user_id in interviewer_ids:
            db.add(InterviewInterviewer(interview_id=interview_id, user_id=user_id))

    await db.commit()

    result2 = await db.execute(
        select(Interview).options(selectinload(Interview.interviewers))
        .where(Interview.id == interview_id)
    )
    return _to_out(result2.scalar_one())


@router.delete("/{interview_id}", status_code=204)
async def delete_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("interviews", "delete")),
):
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch phỏng vấn")
    await db.delete(interview)
    await db.commit()
