from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from app.core.templates import templates

from app.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.interview import Interview, InterviewInterviewer
from datetime import date, timedelta, datetime
from app.deps import get_db, get_current_user_ui
from app.models.user import User

router = APIRouter(prefix="/ui/dashboard", tags=["ui"])

@router.get("", response_class=HTMLResponse)
async def read_dashboard(
    request: Request, 
    period: str = 'this_month', 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_ui)
):
    today = date.today()
    now = datetime.now()
    start_date = None
    
    # Đồng bộ trạng thái phỏng vấn (scheduled -> completed)
    from sqlalchemy import update
    await db.execute(
        update(Interview)
        .where(Interview.status == "scheduled")
        .where(Interview.end_at < now)
        .values(status="completed")
    )
    await db.commit()

    if period == '7d':
        start_date = today - timedelta(days=7)
    elif period == '30d':
        start_date = today - timedelta(days=30)
    elif period == 'this_month':
        start_date = today.replace(day=1)
    elif period == 'this_year':
        start_date = today.replace(month=1, day=1)
    elif period == 'all':
        start_date = None
    else:
        period = '30d'
        start_date = today - timedelta(days=30)
        
    def filter_by_date(stmt):
        if start_date:
            return stmt.where(Candidate.applied_date >= start_date)
        return stmt

    # Calculate stats
    res_jobs = await db.execute(select(func.count()).select_from(Job).where(Job.status == 'open'))
    open_jobs = res_jobs.scalar() or 0
    
    # upcoming_ints_count cũng cần lọc theo user nếu không phải admin
    ints_stmt = select(func.count()).select_from(Interview).where(Interview.status == 'scheduled')
    if user.role != "admin":
        ints_stmt = ints_stmt.outerjoin(InterviewInterviewer).where(
            (Interview.created_by == user.id) | (InterviewInterviewer.user_id == user.id)
        )
    res_ints = await db.execute(ints_stmt)
    upcoming_ints_count = res_ints.scalar() or 0
    
    res_cands = await db.execute(filter_by_date(select(func.count()).select_from(Candidate)))
    total_cands = res_cands.scalar() or 0
    
    res_new_cands = await db.execute(filter_by_date(select(func.count()).select_from(Candidate).where(Candidate.status == 'mới')))
    new_cands = res_new_cands.scalar() or 0
    
    # Candidate status breakdown
    res_status = await db.execute(
        filter_by_date(select(Candidate.status, func.count(Candidate.id)).group_by(Candidate.status))
    )
    status_counts = dict(res_status.all())
    
    # Conversion Metrics
    res_offers = await db.execute(filter_by_date(select(func.count()).select_from(Candidate).where(Candidate.status.in_(['gửi offer', 'đã tuyển']))))
    total_offers = res_offers.scalar() or 0
    
    res_hires = await db.execute(filter_by_date(select(func.count()).select_from(Candidate).where(Candidate.status == 'đã tuyển')))
    total_hires = res_hires.scalar() or 0
    
    offer_acceptance_rate = round((total_hires / total_offers * 100) if total_offers > 0 else 0, 1)
    
    # Application Trend Chart
    chart_start_date = start_date if start_date else today.replace(day=1)
    days_diff = (today - chart_start_date).days
    
    res_trend = await db.execute(
        select(Candidate.applied_date, func.count(Candidate.id))
        .where(Candidate.applied_date >= chart_start_date)
        .group_by(Candidate.applied_date)
        .order_by(Candidate.applied_date.asc())
    )
    trend_raw = res_trend.all()
    # Fill missing dates to make chart continuous
    trend_dict = {row[0]: row[1] for row in trend_raw if row[0]}
    
    chart_labels = []
    chart_data = []
    for i in range(days_diff, -1, -1):
        d = today - timedelta(days=i)
        chart_labels.append(d.strftime('%d/%m'))
        chart_data.append(trend_dict.get(d, 0))
        
    # Upcoming Intervews: Lọc theo user và giới hạn 3
    upcoming_stmt = (
        select(Interview)
        .options(
            selectinload(Interview.candidate).selectinload(Candidate.job), 
            selectinload(Interview.interviewers).selectinload(InterviewInterviewer.user)
        )
        .where(Interview.status == "scheduled")
        .order_by(Interview.scheduled_at.asc())
        .limit(3)
    )
    
    if user.role != "admin":
        upcoming_stmt = upcoming_stmt.outerjoin(InterviewInterviewer).where(
            (Interview.created_by == user.id) | (InterviewInterviewer.user_id == user.id)
        )
    
    res_upcoming_ints = await db.execute(upcoming_stmt)
    upcoming_interviews = res_upcoming_ints.scalars().unique().all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "period": period,
        "role": user.role,
        "open_jobs": open_jobs,
        "total_cands": total_cands,
        "new_cands": new_cands,
        "upcoming_ints_count": upcoming_ints_count,
        "status_counts": status_counts,
        "upcoming_interviews": upcoming_interviews,
        "offer_acceptance_rate": offer_acceptance_rate,
        "total_hires": total_hires,
        "chart_labels": chart_labels,
        "chart_data": chart_data
    })
