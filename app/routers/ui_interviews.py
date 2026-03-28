from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from app.core.templates import templates
from typing import Optional
from datetime import datetime

from app.deps import get_db, require_ui_permission
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.interview import Interview, InterviewInterviewer
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.user import User

router = APIRouter(
    prefix="/ui/interviews", 
    tags=["ui-interviews"],
    dependencies=[Depends(require_ui_permission("interviews", "read"))]
)

from datetime import date
from sqlalchemy import func

@router.get("", response_class=HTMLResponse)
async def list_interviews_ui(
    request: Request, 
    tab: str = "upcoming", 
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    # Cập nhật tức thì các lịch đã kết thúc trước khi lấy danh sách hiển thị
    from sqlalchemy import update
    now = datetime.now()
    await db.execute(
        update(Interview)
        .where(Interview.status == "scheduled")
        .where(Interview.end_at < now)
        .values(status="completed")
    )
    await db.commit()

    user = request.state.user
    
    stmt = select(Interview).options(
        selectinload(Interview.candidate).selectinload(Candidate.job).selectinload(Job.branch),
        selectinload(Interview.interviewers).selectinload(InterviewInterviewer.user)
    )
    
    # Phân quyền: Nếu không phải admin, chỉ thấy lịch do mình tạo hoặc mình phỏng vấn
    if user.role != "admin":
        from sqlalchemy import or_
        # Join để lọc theo người phỏng vấn
        stmt = stmt.outerjoin(InterviewInterviewer).where(
            or_(
                Interview.created_by == user.id,
                InterviewInterviewer.user_id == user.id
            )
        )
    
    if tab == "past":
        stmt = stmt.where(Interview.status == "completed")
        stmt = stmt.order_by(Interview.scheduled_at.desc())
    elif tab == "cancelled":
        stmt = stmt.where(Interview.status == "cancelled")
        stmt = stmt.order_by(Interview.scheduled_at.desc())
    else:
        stmt = stmt.where(Interview.status == "scheduled")
        stmt = stmt.order_by(Interview.scheduled_at.asc())
        
    import math
    count_result = await db.execute(select(func.count()).select_from(stmt.with_only_columns(Interview.id).subquery()))
    total = count_result.scalar_one()
    total_pages = math.ceil(total / size) if total > 0 else 1
    
    stmt = stmt.offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    interviews = result.scalars().unique().all()

    # Lấy toàn bộ ngày phỏng vấn để hiển thị trên Lịch (không bị lọc theo tab)
    all_dates_res = await db.execute(select(Interview.scheduled_at))
    all_dates = [d[0] for d in all_dates_res.all()]

    context = {
        "request": request, 
        "interviews": interviews, 
        "all_dates": all_dates,
        "tab": tab,
        "page": page,
        "size": size,
        "total": total,
        "total_pages": total_pages
    }
    
    hx_target = request.headers.get("hx-target")
    if request.headers.get("hx-request") and hx_target == "interviews-timeline-wrapper":
        return templates.TemplateResponse("interviews/partials/list_body.html", context)
        
    return templates.TemplateResponse("interviews/list.html", context)

@router.get("/form", response_class=HTMLResponse)
async def new_interview_form(request: Request, job_id: Optional[int] = None, candidate_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import or_
    stmt = select(Candidate).options(selectinload(Candidate.job).selectinload(Job.branch)).where(
        or_(Candidate.status == 'duyệt', Candidate.status == 'phỏng vấn')
    )
    if job_id:
        stmt = stmt.where(Candidate.job_id == job_id)
    if candidate_id:
        stmt = select(Candidate).options(selectinload(Candidate.job).selectinload(Job.branch)).where(
            or_(Candidate.status == 'duyệt', Candidate.status == 'phỏng vấn', Candidate.id == candidate_id)
        )
        if job_id:
            stmt = stmt.where(Candidate.job_id == job_id)
        
    result = await db.execute(stmt)
    candidates = result.scalars().all()
    
    res_users = await db.execute(select(User).where(User.is_active == True))
    users = res_users.scalars().all()
    
    from app.models.setting import SystemSetting
    res_conf = await db.execute(select(SystemSetting).where(SystemSetting.key == "interview_webhook_url"))
    conf = res_conf.scalar_one_or_none()
    webhook_url = conf.value if conf else "https://n8n-auto.phucmeo.id.vn/webhook-test/tao-lich-hen"
    
    return templates.TemplateResponse("interviews/form.html", {
        "request": request, 
        "interview": None, 
        "candidates": candidates, 
        "users": users, 
        "selected_candidate_id": candidate_id,
        "webhook_url": webhook_url
    })

@router.get("/form/{interview_id}", response_class=HTMLResponse)
async def edit_interview_form(request: Request, interview_id: int, db: AsyncSession = Depends(get_db)):
    res_int = await db.execute(select(Interview).options(selectinload(Interview.interviewers)).where(Interview.id == interview_id))
    interview = res_int.scalar_one_or_none()
    from sqlalchemy import or_
    res_cand = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.job).selectinload(Job.branch))
        .where(or_(Candidate.status == 'duyệt', Candidate.id == interview.candidate_id))
    )
    candidates = res_cand.scalars().all()
    
    res_users = await db.execute(select(User).where(User.is_active == True))
    users = res_users.scalars().all()
    
    from app.models.setting import SystemSetting
    res_conf = await db.execute(select(SystemSetting).where(SystemSetting.key == "interview_webhook_url"))
    conf = res_conf.scalar_one_or_none()
    webhook_url = conf.value if conf else "https://n8n-auto.phucmeo.id.vn/webhook-test/tao-lich-hen"
    
    return templates.TemplateResponse("interviews/form.html", {
        "request": request, 
        "interview": interview, 
        "candidates": candidates, 
        "users": users,
        "webhook_url": webhook_url
    })

@router.get("/{interview_id}", response_class=HTMLResponse)
async def view_interview_detail_ui(request: Request, interview_id: int, db: AsyncSession = Depends(get_db)):
    # Cập nhật trạng thái nếu đã quá giờ
    from sqlalchemy import update
    now = datetime.now()
    await db.execute(
        update(Interview)
        .where(Interview.id == interview_id)
        .where(Interview.status == "scheduled")
        .where(Interview.end_at < now)
        .values(status="completed")
    )
    await db.commit()

    user = request.state.user
    stmt = select(Interview).options(
        selectinload(Interview.candidate).selectinload(Candidate.job).selectinload(Job.branch),
        selectinload(Interview.interviewers).selectinload(InterviewInterviewer.user)
    ).where(Interview.id == interview_id)
    
    result = await db.execute(stmt)
    interview = result.scalar_one_or_none()
    
    if not interview:
        return HTMLResponse("Không tìm thấy", status_code=404)
        
    # Phân quyền: Check nếu không phải admin và không có quyền liên quan
    if user.role != "admin":
        is_interviewer = any(i.user_id == user.id for i in interview.interviewers)
        if interview.created_by != user.id and not is_interviewer:
            return HTMLResponse("Bạn không có quyền xem lịch hẹn này", status_code=403)
            
    return templates.TemplateResponse("interviews/detail.html", {"request": request, "interview": interview})

@router.delete("/{interview_id}", response_class=HTMLResponse)
async def delete_interview_ui(request: Request, interview_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_ui_permission("interviews", "delete"))):
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    intv = result.scalar_one_or_none()
    if intv:
        await db.delete(intv)
        await db.commit()
    return HTMLResponse("")

from typing import List

from app.models.interview import InterviewType, InterviewStatus

@router.post("", response_class=HTMLResponse)
async def create_interview_ui(
    request: Request,
    candidate_id: int = Form(...),
    scheduled_at: str = Form(...),
    end_at: str = Form(...),
    interview_type: str = Form(...),
    location: Optional[str] = Form(None),
    online_link: Optional[str] = Form(None),
    status: str = Form("scheduled"),
    interviewer_ids: List[int] = Form([]),
    webhook_url: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("interviews", "create"))
):
    user = request.state.user
    sch_time = datetime.fromisoformat(scheduled_at)
    end_time = datetime.fromisoformat(end_at)
    
    new_intv = Interview(
        candidate_id=candidate_id,
        scheduled_at=sch_time,
        end_at=end_time,
        interview_type=interview_type,
        location=location,
        online_link=online_link,
        status=status,
        created_by=user.id
    )
    db.add(new_intv)
    
    # Add Interviewers
    for uid in interviewer_ids:
        db.add(InterviewInterviewer(interview=new_intv, user_id=uid))
        
    # Update candidate status
    res_cand = await db.execute(select(Candidate).options(selectinload(Candidate.job).selectinload(Job.branch)).where(Candidate.id == candidate_id))
    cand = res_cand.scalar_one_or_none()
    if cand:
        cand.status = 'phỏng vấn'
        db.add(cand)

    await db.commit()
    await db.refresh(new_intv)
    
    res = await db.execute(select(Interview).options(selectinload(Interview.candidate).selectinload(Candidate.job).selectinload(Job.branch), selectinload(Interview.interviewers).selectinload(InterviewInterviewer.user)).where(Interview.id == new_intv.id))
    new_intv = res.scalar_one_or_none()
    
    if webhook_url:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Lấy danh sách thông tin người phỏng vấn để gửi webhook
                interviewers_data = [
                    {"name": i.user.full_name, "email": i.user.email} 
                    for i in new_intv.interviewers
                ]
                
                payload = {
                    "interview_id": new_intv.id,
                    "candidate_id": cand.id if cand else candidate_id,
                    "candidate_name": cand.full_name if cand else "N/A",
                    "candidate_email": cand.email if cand else "",
                    "candidate_phone": cand.phone if cand else "",
                    "job_title": cand.job.title if (cand and cand.job) else "N/A",
                    "branch_name": cand.job.branch.name if (cand and cand.job and cand.job.branch) else "N/A",
                    "interviewers": interviewers_data,
                    "scheduled_at": scheduled_at,
                    "end_at": end_at,
                    "interview_type": interview_type,
                    "location": location if interview_type == 'offline' else "Online",
                    "source": "SmartCV Auto UI"
                }
                await client.post(webhook_url, json=payload)
        except Exception as e:
            print(f"Error sending interview webhook: {e}")
            
        # Update Webhook URL
        from app.models.setting import SystemSetting
        res_conf = await db.execute(select(SystemSetting).where(SystemSetting.key == "interview_webhook_url"))
        conf = res_conf.scalar_one_or_none()
        if not conf:
            new_conf = SystemSetting(key="interview_webhook_url", value=webhook_url)
            db.add(new_conf)
        elif conf.value != webhook_url:
            conf.value = webhook_url
        await db.commit()
    
    return templates.TemplateResponse("interviews/row.html", {"request": request, "interview": new_intv, "loop_index": 0})

@router.post("/{interview_id}/update", response_class=HTMLResponse)
async def update_interview_ui(
    request: Request,
    interview_id: int,
    candidate_id: int = Form(...),
    scheduled_at: str = Form(...),
    end_at: str = Form(...),
    interview_type: str = Form(...),
    location: Optional[str] = Form(None),
    online_link: Optional[str] = Form(None),
    status: str = Form("scheduled"),
    interviewer_ids: List[int] = Form([]),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("interviews", "update"))
):
    res_int = await db.execute(select(Interview).options(selectinload(Interview.interviewers)).where(Interview.id == interview_id))
    intv = res_int.scalar_one_or_none()
    if intv:
        intv.candidate_id = candidate_id
        try:
            intv.scheduled_at = datetime.fromisoformat(scheduled_at)
        except ValueError:
            pass
        try:
            intv.end_at = datetime.fromisoformat(end_at)
        except ValueError:
            pass
            
        intv.interview_type = interview_type
        intv.location = location
        intv.online_link = online_link
        intv.status = status
        
        # Update interviewers (Correct way to avoid SAWarning)
        # Clear existing and add new
        intv.interviewers = [InterviewInterviewer(user_id=uid) for uid in interviewer_ids]
            
        # Update candidate status
        res_cand = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        cand = res_cand.scalar_one_or_none()
        if cand and cand.status != 'phỏng vấn':
            cand.status = 'phỏng vấn'
            db.add(cand)
            
        await db.commit()
        await db.refresh(intv)
        
        res = await db.execute(select(Interview).options(selectinload(Interview.candidate).selectinload(Candidate.job).selectinload(Job.branch), selectinload(Interview.interviewers).selectinload(InterviewInterviewer.user)).where(Interview.id == intv.id))
        intv = res.scalar_one_or_none()

    return templates.TemplateResponse("interviews/row.html", {"request": request, "interview": intv})
