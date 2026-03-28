from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from app.core.templates import templates
from typing import Optional

from app.deps import get_db, require_ui_permission
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.models.job import Job, JobSkill
from app.models.department import Skill, Department, Branch
from app.models.candidate import Candidate
from app.models.interview import Interview, InterviewInterviewer

router = APIRouter(
    prefix="/ui/jobs", 
    tags=["ui-jobs"],
    dependencies=[Depends(require_ui_permission("jobs", "read"))]
)

from sqlalchemy import or_, func
import math

@router.get("", response_class=HTMLResponse)
async def list_jobs_ui(
    request: Request, 
    q: Optional[str] = None, 
    status: Optional[str] = None,
    department_id: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Job).options(selectinload(Job.department), selectinload(Job.branch), selectinload(Job.candidates))
    
    # Filter by search term
    if q:
        stmt = stmt.join(Job.department, isouter=True).where(or_(
            Job.title.ilike(f"%{q}%"),
            Department.name.ilike(f"%{q}%")
        ))
        
    # Additional filters
    if status:
        stmt = stmt.where(Job.status == status)
    if department_id and str(department_id).strip():
        try:
            stmt = stmt.where(Job.department_id == int(department_id))
        except ValueError:
            pass
        
    # Count total
    count_result = await db.execute(select(func.count()).select_from(stmt.with_only_columns(Job.id).subquery()))
    total = count_result.scalar_one()
    total_pages = math.ceil(total / size) if total > 0 else 1
    
    # Sorting
    _SORTABLE_FIELDS = {
        "title": Job.title,
        "status": Job.status,
        "quantity": Job.quantity,
        "created_at": Job.created_at,
    }
    sort_col = _SORTABLE_FIELDS.get(sort_by, Job.created_at)
    if sort_order.lower() == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())
        
    # Pagination
    stmt = stmt.offset((page - 1) * size).limit(size)
    
    result = await db.execute(stmt)
    jobs = result.scalars().unique().all()
    
    # Load departments for filter dropdown
    dept_res = await db.execute(select(Department).order_by(Department.name))
    departments = dept_res.scalars().all()
    
    # --- GLOBAL STATS FOR CARDS ---
    stats_stmt = select(
        func.count().label("total"),
        func.count().filter(Job.status == "open").label("open"),
        func.count().filter(Job.status == "closed").label("closed")
    ).select_from(Job)
    stats_result = await db.execute(stats_stmt)
    stats = stats_result.one()
    
    context = {
        "request": request, 
        "jobs": jobs,
        "departments": departments,
        "total": total, # This is filtered total for pagination
        "total_jobs": stats.total, # Global total
        "open_jobs": stats.open,
        "closed_jobs": stats.closed,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "q": q or "",
        "status": status or "",
        "department_id": department_id or "",
        "sort_by": sort_by,
        "sort_order": sort_order
    }
    
    hx_target = request.headers.get("hx-target")
    if request.headers.get("hx-request") and hx_target == "jobs-list-container":
        return templates.TemplateResponse("jobs/partials/list_body.html", context)
        
    return templates.TemplateResponse("jobs/list.html", context)

@router.delete("/{job_id}", response_class=HTMLResponse)
async def delete_job_ui(request: Request, job_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_ui_permission("jobs", "delete"))):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job:
        await db.delete(job)
        await db.commit()
    return HTMLResponse("")

@router.get("/form", response_class=HTMLResponse)
async def new_job_form(request: Request, db: AsyncSession = Depends(get_db)):
    result_skills = await db.execute(select(Skill).order_by(Skill.name))
    skills = result_skills.scalars().all()
    
    result_depts = await db.execute(select(Department).order_by(Department.name))
    departments = result_depts.scalars().all()
    
    result_branches = await db.execute(select(Branch).order_by(Branch.name))
    branches = result_branches.scalars().all()
    
    return templates.TemplateResponse("jobs/form.html", {
        "request": request, 
        "job": None, 
        "skills": skills, 
        "departments": departments,
        "branches": branches
    })

@router.get("/form/{job_id}", response_class=HTMLResponse)
async def edit_job_form(request: Request, job_id: int, context: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).options(selectinload(Job.skills)).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    result_skills = await db.execute(select(Skill).order_by(Skill.name))
    skills = result_skills.scalars().all()
    
    result_depts = await db.execute(select(Department).order_by(Department.name))
    departments = result_depts.scalars().all()
    
    result_branches = await db.execute(select(Branch).order_by(Branch.name))
    branches = result_branches.scalars().all()
    
    return templates.TemplateResponse("jobs/form.html", {
        "request": request, 
        "job": job, 
        "skills": skills, 
        "departments": departments, 
        "branches": branches,
        "context": context
    })

@router.post("", response_class=HTMLResponse)
async def create_job_ui(
    request: Request,
    title: str = Form(...),
    department_id: Optional[str] = Form(None),
    branch_id: Optional[str] = Form(None),
    status: str = Form("open"),
    salary_min: Optional[int] = Form(None),
    salary_max: Optional[int] = Form(None),
    salary_currency: Optional[str] = Form(None),
    experience_level: Optional[str] = Form(None),
    education_level: Optional[str] = Form(None),
    quantity: Optional[int] = Form(1),
    description: Optional[str] = Form(None),
    requirements: Optional[str] = Form(None),
    benefits: Optional[str] = Form(None),
    skill_ids: list[int] = Form(default=[]),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_ui_permission("jobs", "create"))
):
    # Convert string IDs to int safely
    dept_id = int(department_id) if department_id and department_id.strip() else None
    br_id = int(branch_id) if branch_id and branch_id.strip() else None

    new_job = Job(
        title=title,
        department_id=dept_id,
        branch_id=br_id,
        status=status,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        experience_level=experience_level,
        education_level=education_level,
        quantity=quantity,
        description=description,
        requirements=requirements,
        benefits=benefits,
        created_by=user.id
    )
    db.add(new_job)
    await db.flush()
    
    for sid in skill_ids:
        db.add(JobSkill(job_id=new_job.id, skill_id=sid))
        
    await db.commit()
    
    result = await db.execute(select(Job).options(selectinload(Job.department), selectinload(Job.branch), selectinload(Job.candidates)).where(Job.id == new_job.id))
    new_job = result.scalar_one_or_none()
    
    return templates.TemplateResponse("jobs/row.html", {"request": request, "job": new_job, "loop_index": 0})

@router.post("/{job_id}/update", response_class=HTMLResponse)
async def update_job_ui(
    request: Request,
    job_id: int,
    title: str = Form(...),
    department_id: Optional[str] = Form(None),
    branch_id: Optional[str] = Form(None),
    status: str = Form("open"),
    salary_min: Optional[int] = Form(None),
    salary_max: Optional[int] = Form(None),
    salary_currency: Optional[str] = Form(None),
    experience_level: Optional[str] = Form(None),
    education_level: Optional[str] = Form(None),
    quantity: Optional[int] = Form(1),
    description: Optional[str] = Form(None),
    requirements: Optional[str] = Form(None),
    benefits: Optional[str] = Form(None),
    skill_ids: list[int] = Form(default=[]),
    context: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("jobs", "update"))
):
    # Convert string IDs to int safely
    dept_id = int(department_id) if department_id and department_id.strip() else None
    br_id = int(branch_id) if branch_id and branch_id.strip() else None

    result = await db.execute(select(Job).options(selectinload(Job.candidates), selectinload(Job.department), selectinload(Job.branch)).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job:
        job.title = title
        job.department_id = dept_id
        job.branch_id = br_id
        job.status = status
        job.salary_min = salary_min
        job.salary_max = salary_max
        job.salary_currency = salary_currency
        job.experience_level = experience_level
        job.education_level = education_level
        job.quantity = quantity
        job.description = description
        job.requirements = requirements
        job.benefits = benefits
        
        await db.execute(delete(JobSkill).where(JobSkill.job_id == job_id))
        for sid in skill_ids:
            db.add(JobSkill(job_id=job.id, skill_id=sid))
            
        await db.commit()
        await db.refresh(job)
    
    if context == 'detail':
        return HTMLResponse(content="", headers={"HX-Refresh": "true"})
        
    return templates.TemplateResponse("jobs/row.html", {"request": request, "job": job})

# --- JOB DETAIL VIEW ---
@router.get("/{job_id}/detail", response_class=HTMLResponse)
async def job_detail_view(request: Request, job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.department), selectinload(Job.branch), selectinload(Job.skills).selectinload(JobSkill.skill), selectinload(Job.candidates))
        .where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        return HTMLResponse("Job not found", status_code=404)
    return templates.TemplateResponse("jobs/detail.html", {"request": request, "job": job})

@router.get("/{job_id}/tab/info", response_class=HTMLResponse)
async def job_tab_info(request: Request, job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.department), selectinload(Job.branch), selectinload(Job.skills).selectinload(JobSkill.skill), selectinload(Job.candidates))
        .where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    return templates.TemplateResponse("jobs/tabs/info.html", {"request": request, "job": job})

@router.get("/{job_id}/tab/candidates", response_class=HTMLResponse)
async def job_tab_candidates(request: Request, job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Candidate).where(Candidate.job_id == job_id).order_by(Candidate.id.desc())
    )
    candidates = result.scalars().all()
    return templates.TemplateResponse("jobs/tabs/candidates.html", {"request": request, "candidates": candidates, "job_id": job_id})

@router.get("/{job_id}/tab/interviews", response_class=HTMLResponse)
async def job_tab_interviews(request: Request, job_id: int, db: AsyncSession = Depends(get_db)):
    # Phỏng vấn của ứng viên nộp cho job_id này
    result = await db.execute(
        select(Interview)
        .join(Candidate)
        .options(
            selectinload(Interview.candidate).selectinload(Candidate.job).selectinload(Job.branch),
            selectinload(Interview.interviewers).selectinload(InterviewInterviewer.user)
        )
        .where(Candidate.job_id == job_id)
        .order_by(Interview.scheduled_at.desc())
    )
    interviews = result.scalars().all()
    return templates.TemplateResponse("jobs/tabs/interviews.html", {"request": request, "interviews": interviews, "job_id": job_id})
