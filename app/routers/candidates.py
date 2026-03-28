from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.deps import get_current_user, require_permission
from app.models.candidate import (
    Candidate, CandidateLink, CandidateEducation,
    CandidateExperience, CandidateSkill, CandidateNote,
)
from app.models.user import User
from app.schemas.candidate import (
    CandidateCreate, CandidateUpdate, CandidateOut,
    CandidateListItem, CandidateNoteCreate, CandidateNoteUpdate, CandidateNoteOut,
    CandidateEducationBase, CandidateEducationUpdate, CandidateEducationOut,
    CandidateExperienceBase, CandidateExperienceUpdate, CandidateExperienceOut,
    CandidateLinkBase, CandidateLinkUpdate, CandidateLinkOut,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _candidate_options():
    return [
        selectinload(Candidate.links),
        selectinload(Candidate.education),
        selectinload(Candidate.experience),
        selectinload(Candidate.skills),
        selectinload(Candidate.notes),
    ]


_SORTABLE_FIELDS = {
    "applied_date": Candidate.applied_date,
    "full_name":    Candidate.full_name,
    "score":        Candidate.score,
    "status":       Candidate.status,
    "created_at":   Candidate.created_at,
}


# ── LIST ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[CandidateListItem],
            summary="Danh sách ứng viên (có phân trang, tìm kiếm, lọc, sắp xếp)")
async def list_candidates(
    # ── Filters ────────────────────────────────────────────
    job_id:     Optional[int]  = Query(None, description="Lọc theo job"),
    status:     Optional[str]  = Query(None, description="Lọc theo trạng thái (new, reviewing, interviewed, offered, hired, rejected)"),
    q:          Optional[str]  = Query(None, description="Tìm kiếm theo tên, email, số điện thoại"),
    from_date:  Optional[date] = Query(None, description="Ngày apply từ (applied_date >=), format: YYYY-MM-DD"),
    to_date:    Optional[date] = Query(None, description="Ngày apply đến (applied_date <=), format: YYYY-MM-DD"),
    # ── Sorting ─────────────────────────────────────────────
    sort_by:    str            = Query("applied_date", description="Trường sắp xếp: applied_date | full_name | score | status | created_at"),
    sort_order: str            = Query("desc",         description="asc | desc"),
    # ── Pagination ──────────────────────────────────────────
    page: int         = Query(1,  ge=1,        description="Trang hiện tại (bắt đầu từ 1)"),
    size: int         = Query(20, ge=1, le=100, description="Số bản ghi mỗi trang (tối đa 100)"),
    db: AsyncSession  = Depends(get_db),
    current_user: User = Depends(require_permission("candidates", "read")),
):
    query = select(Candidate)

    # Role-based filter
    user_role = current_user.role if isinstance(current_user.role, str) else current_user.role.value
    if user_role == "interviewer":
        from app.models.interview import InterviewInterviewer, Interview
        subq = (
            select(Interview.candidate_id)
            .join(InterviewInterviewer, InterviewInterviewer.interview_id == Interview.id)
            .where(InterviewInterviewer.user_id == current_user.id)
            .scalar_subquery()
        )
        query = query.where(Candidate.id.in_(subq))

    # Filters
    if job_id:
        query = query.where(Candidate.job_id == job_id)
    if status:
        query = query.where(Candidate.status == status)
    if q:
        keyword = f"%{q.strip()}%"
        query = query.where(or_(
            Candidate.full_name.ilike(keyword),
            Candidate.email.ilike(keyword),
            Candidate.phone.ilike(keyword),
        ))
    if from_date:
        query = query.where(Candidate.applied_date >= from_date)
    if to_date:
        query = query.where(Candidate.applied_date <= to_date)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    sort_col = _SORTABLE_FIELDS.get(sort_by, Candidate.applied_date)
    query = query.order_by(sort_col.asc() if sort_order.lower() == "asc" else sort_col.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    return PaginatedResponse(total=total, page=page, size=size, items=result.scalars().all())


# ── CREATE ────────────────────────────────────────────────────────────────────

@router.post("", response_model=CandidateOut, status_code=201,
             summary="Tạo ứng viên mới (kèm kinh nghiệm, học vấn, links trong 1 lần gọi)")
async def create_candidate(
    body: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("candidates", "create")),
):
    candidate = Candidate(
        full_name=body.full_name,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        phone=body.phone,
        email=body.email,
        facebook=body.facebook,
        specific_address=body.specific_address,
        job_id=body.job_id,
        cv_link=body.cv_link,
        portfolio_link=body.portfolio_link,
        ai_summary=body.ai_summary,
        score=body.score,
        status=body.status,
        applied_date=body.applied_date,
        assigned_to=body.assigned_to,
        created_by=current_user.id,
    )
    db.add(candidate)
    await db.flush()

    for link in (body.links or []):
        db.add(CandidateLink(candidate_id=candidate.id, label=link.label, url=link.url))
    for edu in (body.education or []):
        db.add(CandidateEducation(candidate_id=candidate.id, **edu.model_dump()))
    for exp in (body.experience or []):
        db.add(CandidateExperience(candidate_id=candidate.id, **exp.model_dump()))
    for skill_id in (body.skill_ids or []):
        db.add(CandidateSkill(candidate_id=candidate.id, skill_id=skill_id))

    await db.commit()
    result = await db.execute(
        select(Candidate).options(*_candidate_options()).where(Candidate.id == candidate.id)
    )
    return result.scalar_one()


# ── GET DETAIL ────────────────────────────────────────────────────────────────

@router.get("/{candidate_id}", response_model=CandidateOut, summary="Chi tiết ứng viên")
async def get_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("candidates", "read")),
):
    result = await db.execute(
        select(Candidate).options(*_candidate_options())
        .where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Không tìm thấy ứng viên")
    return candidate


# ── UPDATE MAIN INFO ──────────────────────────────────────────────────────────

@router.post("/{candidate_id}/update", response_model=CandidateOut,
             summary="Cập nhật thông tin cơ bản của ứng viên")
async def update_candidate(
    candidate_id: int,
    body: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    result = await db.execute(
        select(Candidate).options(*_candidate_options())
        .where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Không tìm thấy ứng viên")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(candidate, field, val)

    await db.commit()
    result2 = await db.execute(
        select(Candidate).options(*_candidate_options()).where(Candidate.id == candidate_id)
    )
    return result2.scalar_one()


@router.delete("/{candidate_id}", status_code=204, summary="Xóa ứng viên (hard delete)")
async def delete_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "delete")),
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Không tìm thấy ứng viên")
    await db.delete(candidate)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# SUB-RESOURCES
# ═══════════════════════════════════════════════════════════════════════════════

# ── NOTES ─────────────────────────────────────────────────────────────────────

@router.post("/{candidate_id}/notes", response_model=CandidateNoteOut, status_code=201,
             summary="Thêm ghi chú cho ứng viên")
async def add_note(
    candidate_id: int,
    body: CandidateNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("candidates", "update")),
):
    note = CandidateNote(
        candidate_id=candidate_id,
        created_by=current_user.id,
        content=body.content,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.post("/{candidate_id}/notes/{note_id}/update", response_model=CandidateNoteOut,
             summary="Sửa nội dung ghi chú")
async def update_note(
    candidate_id: int,
    note_id: int,
    body: CandidateNoteUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    result = await db.execute(
        select(CandidateNote).where(
            CandidateNote.id == note_id,
            CandidateNote.candidate_id == candidate_id,
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi chú")
    note.content = body.content
    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/{candidate_id}/notes/{note_id}", status_code=204,
               summary="Xóa ghi chú")
async def delete_note(
    candidate_id: int,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    result = await db.execute(
        select(CandidateNote).where(
            CandidateNote.id == note_id,
            CandidateNote.candidate_id == candidate_id,
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi chú")
    await db.delete(note)
    await db.commit()


# ── EDUCATION ─────────────────────────────────────────────────────────────────

@router.post("/{candidate_id}/education", response_model=CandidateEducationOut, status_code=201,
             summary="Thêm học vấn cho ứng viên")
async def add_education(
    candidate_id: int,
    body: CandidateEducationBase,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    edu = CandidateEducation(candidate_id=candidate_id, **body.model_dump())
    db.add(edu)
    await db.commit()
    await db.refresh(edu)
    return edu


@router.post("/{candidate_id}/education/{edu_id}/update", response_model=CandidateEducationOut,
             summary="Sửa thông tin học vấn")
async def update_education(
    candidate_id: int,
    edu_id: int,
    body: CandidateEducationUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    result = await db.execute(
        select(CandidateEducation).where(
            CandidateEducation.id == edu_id,
            CandidateEducation.candidate_id == candidate_id,
        )
    )
    edu = result.scalar_one_or_none()
    if not edu:
        raise HTTPException(status_code=404, detail="Không tìm thấy học vấn")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(edu, field, val)
    await db.commit()
    await db.refresh(edu)
    return edu


@router.delete("/{candidate_id}/education/{edu_id}", status_code=204,
               summary="Xóa học vấn")
async def delete_education(
    candidate_id: int,
    edu_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    result = await db.execute(
        select(CandidateEducation).where(
            CandidateEducation.id == edu_id,
            CandidateEducation.candidate_id == candidate_id,
        )
    )
    edu = result.scalar_one_or_none()
    if not edu:
        raise HTTPException(status_code=404, detail="Không tìm thấy học vấn")
    await db.delete(edu)
    await db.commit()


# ── EXPERIENCE ────────────────────────────────────────────────────────────────

@router.post("/{candidate_id}/experience", response_model=CandidateExperienceOut, status_code=201,
             summary="Thêm kinh nghiệm cho ứng viên")
async def add_experience(
    candidate_id: int,
    body: CandidateExperienceBase,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    exp = CandidateExperience(candidate_id=candidate_id, **body.model_dump())
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return exp


@router.post("/{candidate_id}/experience/{exp_id}/update", response_model=CandidateExperienceOut,
             summary="Sửa thông tin kinh nghiệm")
async def update_experience(
    candidate_id: int,
    exp_id: int,
    body: CandidateExperienceUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    result = await db.execute(
        select(CandidateExperience).where(
            CandidateExperience.id == exp_id,
            CandidateExperience.candidate_id == candidate_id,
        )
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Không tìm thấy kinh nghiệm")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(exp, field, val)
    await db.commit()
    await db.refresh(exp)
    return exp


@router.delete("/{candidate_id}/experience/{exp_id}", status_code=204,
               summary="Xóa kinh nghiệm")
async def delete_experience(
    candidate_id: int,
    exp_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    result = await db.execute(
        select(CandidateExperience).where(
            CandidateExperience.id == exp_id,
            CandidateExperience.candidate_id == candidate_id,
        )
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Không tìm thấy kinh nghiệm")
    await db.delete(exp)
    await db.commit()


# ── LINKS ─────────────────────────────────────────────────────────────────────

@router.post("/{candidate_id}/links", response_model=CandidateLinkOut, status_code=201,
             summary="Thêm liên kết (GitHub, Portfolio...) cho ứng viên")
async def add_link(
    candidate_id: int,
    body: CandidateLinkBase,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    link = CandidateLink(candidate_id=candidate_id, **body.model_dump())
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.post("/{candidate_id}/links/{link_id}/update", response_model=CandidateLinkOut,
             summary="Sửa liên kết")
async def update_link(
    candidate_id: int,
    link_id: int,
    body: CandidateLinkUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    result = await db.execute(
        select(CandidateLink).where(
            CandidateLink.id == link_id,
            CandidateLink.candidate_id == candidate_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Không tìm thấy liên kết")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(link, field, val)
    await db.commit()
    await db.refresh(link)
    return link


@router.delete("/{candidate_id}/links/{link_id}", status_code=204,
               summary="Xóa liên kết")
async def delete_link(
    candidate_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "update")),
):
    result = await db.execute(
        select(CandidateLink).where(
            CandidateLink.id == link_id,
            CandidateLink.candidate_id == candidate_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Không tìm thấy liên kết")
    await db.delete(link)
    await db.commit()


# ── GET SUB-RESOURCES ────────────────────────────────────────────────────────

@router.get("/{candidate_id}/notes", response_model=List[CandidateNoteOut], summary="Lấy danh sách ghi chú của ứng viên")
async def get_candidate_notes(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "read")),
):
    result = await db.execute(select(CandidateNote).where(CandidateNote.candidate_id == candidate_id).order_by(CandidateNote.created_at.desc()))
    return result.scalars().all()


@router.get("/{candidate_id}/education", response_model=List[CandidateEducationOut], summary="Lấy danh sách học vấn của ứng viên")
async def get_candidate_education(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "read")),
):
    result = await db.execute(select(CandidateEducation).where(CandidateEducation.candidate_id == candidate_id))
    return result.scalars().all()


@router.get("/{candidate_id}/experience", response_model=List[CandidateExperienceOut], summary="Lấy danh sách kinh nghiệm của ứng viên")
async def get_candidate_experience(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "read")),
):
    result = await db.execute(select(CandidateExperience).where(CandidateExperience.candidate_id == candidate_id))
    return result.scalars().all()


@router.get("/{candidate_id}/links", response_model=List[CandidateLinkOut], summary="Lấy danh sách liên kết của ứng viên")
async def get_candidate_links(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "read")),
):
    result = await db.execute(select(CandidateLink).where(CandidateLink.candidate_id == candidate_id))
    return result.scalars().all()


@router.get("/{candidate_id}/skills", response_model=List[int], summary="Lấy danh sách ID kỹ năng của ứng viên")
async def get_candidate_skills(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("candidates", "read")),
):
    result = await db.execute(select(CandidateSkill.skill_id).where(CandidateSkill.candidate_id == candidate_id))
    return result.scalars().all()
