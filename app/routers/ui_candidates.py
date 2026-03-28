from fastapi import APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from app.core.templates import templates
from typing import Optional
import httpx

from app.deps import get_db, require_ui_permission
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.candidate import Candidate, CandidateExperience, CandidateEducation, CandidateSkill, CandidateLink, CandidateNote
from app.models.job import Job
from app.models.department import Branch
from app.models.setting import SystemSetting

router = APIRouter(
    prefix="/ui/candidates", 
    tags=["ui-candidates"], 
    include_in_schema=False,
    dependencies=[Depends(require_ui_permission("candidates", "read"))]
)

def _candidate_options():
    return [
        selectinload(Candidate.job).selectinload(Job.branch),
        selectinload(Candidate.experience),
        selectinload(Candidate.education),
        selectinload(Candidate.skills).selectinload(CandidateSkill.skill),
        selectinload(Candidate.links),
        selectinload(Candidate.notes).selectinload(CandidateNote.author)
    ]

@router.get("/form", response_class=HTMLResponse)
async def new_candidate_form(request: Request, db: AsyncSession = Depends(get_db)):
    # Đối với form thêm mới, jobs sẽ được load động sau khi chọn chi nhánh
    jobs = []
    
    result_branches = await db.execute(select(Branch).order_by(Branch.name))
    branches = result_branches.scalars().all()
    
    # Lấy Webhook URL từ db
    res_conf = await db.execute(select(SystemSetting).where(SystemSetting.key == "candidate_webhook_url"))
    conf = res_conf.scalar_one_or_none()
    webhook_url = conf.value if conf else "https://n8n-auto.phucmeo.id.vn/webhook-test/danh-gia-ung-vien"
    
    return templates.TemplateResponse("candidates/form.html", {
        "request": request, 
        "candidate": None, 
        "jobs": jobs,
        "branches": branches,
        "webhook_url": webhook_url
    })

@router.get("/form/{candidate_id}", response_class=HTMLResponse)
async def edit_candidate_form(request: Request, candidate_id: int, db: AsyncSession = Depends(get_db)):
    res_cand = await db.execute(select(Candidate).options(selectinload(Candidate.job).selectinload(Job.branch)).where(Candidate.id == candidate_id))
    candidate = res_cand.scalar_one_or_none()
    
    res_jobs = await db.execute(select(Job))
    jobs = res_jobs.scalars().all()
    
    result_branches = await db.execute(select(Branch).order_by(Branch.name))
    branches = result_branches.scalars().all()
    
    return templates.TemplateResponse("candidates/form.html", {
        "request": request, 
        "candidate": candidate, 
        "jobs": jobs,
        "branches": branches
    })

@router.get("/jobs-by-branch", response_class=HTMLResponse)
async def jobs_by_branch(request: Request, branch_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    if not branch_id or not branch_id.isdigit():
        return HTMLResponse(content='<option value="">-- Vui lòng chọn chi nhánh trước --</option>')
    
    stmt = select(Job).where(Job.status == "open").where(Job.branch_id == int(branch_id))
    
    result = await db.execute(stmt.order_by(Job.title))
    jobs = result.scalars().all()
    
    html = '<option value="">-- Chọn công việc --</option>'
    if not jobs:
        html = '<option value="">-- Không có vị trí nào đang tuyển tại chi nhánh này --</option>'
    for job in jobs:
        html += f'<option value="{job.id}">{job.title}</option>'
    return HTMLResponse(content=html)

@router.get("/{candidate_id}", response_class=HTMLResponse)
async def candidate_detail_ui(request: Request, candidate_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Candidate).options(*_candidate_options()).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Không tìm thấy ứng viên")
        
    return templates.TemplateResponse("candidates/detail.html", {"request": request, "candidate": candidate})

@router.put("/{candidate_id}/status", response_class=HTMLResponse)
async def update_candidate_status_ui(
    request: Request, 
    candidate_id: int, 
    status: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("candidates", "update"))
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    
    if candidate:
        candidate.status = status
        await db.commit()
    
    response = HTMLResponse("<script>window.location.reload();</script>")
    response.headers["HX-Refresh"] = "true"
    return response

@router.get("/{candidate_id}/offer-form", response_class=HTMLResponse)
async def offer_form_ui(request: Request, candidate_id: int, db: AsyncSession = Depends(get_db)):
    from app.models.setting import SystemSetting
    res_conf = await db.execute(select(SystemSetting).where(SystemSetting.key == "offer_webhook_url"))
    conf = res_conf.scalar_one_or_none()
    webhook_url = conf.value if conf else "https://n8n-auto.phucmeo.id.vn/webhook-test/danh-gia-ung-vien"
    
    return templates.TemplateResponse("candidates/offer_form.html", {
        "request": request, 
        "candidate_id": candidate_id,
        "webhook_url": webhook_url
    })

@router.post("/{candidate_id}/offer", response_class=HTMLResponse)
async def send_offer_ui(
    request: Request,
    candidate_id: int,
    webhook_url: str = Form(...),
    start_date: str = Form(...),
    work_time: str = Form(...),
    salary: str = Form(...),
    work_location: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("candidates", "update"))
):
    import httpx
    from fastapi import HTTPException
    res = await db.execute(select(Candidate).options(*_candidate_options()).where(Candidate.id == candidate_id))
    candidate = res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Not Found")
        
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "candidate_id": candidate.id,
                "full_name": candidate.full_name,
                "email": candidate.email,
                "phone": candidate.phone,
                "job_title": candidate.job.title if candidate.job else "N/A",
                "start_date": start_date,
                "work_time": work_time,
                "salary": salary,
                "work_location": work_location,
                "source": "SmartCV Auto UI"
            }
            await client.post(webhook_url, json=payload)
    except Exception as e:
        print(f"Error sending offer webhook: {e}")

    # Tiến hành lưu lại webhook_url để dùng cho các ứng viên khác
    from app.models.setting import SystemSetting
    res_conf = await db.execute(select(SystemSetting).where(SystemSetting.key == "offer_webhook_url"))
    conf = res_conf.scalar_one_or_none()
    if not conf:
        new_conf = SystemSetting(key="offer_webhook_url", value=webhook_url)
        db.add(new_conf)
    elif conf.value != webhook_url:
        conf.value = webhook_url
        
    candidate.status = "gửi offer"
    await db.commit()
    
    response = HTMLResponse("<script>window.location.reload();</script>")
    response.headers["HX-Refresh"] = "true"
    return response

@router.get("/{candidate_id}/reject-form", response_class=HTMLResponse)
async def reject_form_ui(request: Request, candidate_id: int, db: AsyncSession = Depends(get_db)):
    from app.models.setting import SystemSetting
    res_conf = await db.execute(select(SystemSetting).where(SystemSetting.key == "reject_webhook_url"))
    conf = res_conf.scalar_one_or_none()
    webhook_url = conf.value if conf else "https://n8n-auto.phucmeo.id.vn/webhook-test/tu-choi-ung-vien"
    
    return templates.TemplateResponse("candidates/reject_form.html", {
        "request": request, 
        "candidate_id": candidate_id,
        "webhook_url": webhook_url
    })

@router.post("/{candidate_id}/reject", response_class=HTMLResponse)
async def reject_candidate_ui(
    request: Request,
    candidate_id: int,
    webhook_url: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("candidates", "update"))
):
    import httpx
    res = await db.execute(select(Candidate).options(selectinload(Candidate.job).selectinload(Job.branch)).where(Candidate.id == candidate_id))
    candidate = res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Not Found")
        
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "candidate_id": candidate.id,
                "full_name": candidate.full_name,
                "email": candidate.email,
                "phone": candidate.phone,
                "job_title": candidate.job.title if candidate.job else "N/A",
                "status": "từ chối",
                "source": "SmartCV Auto UI"
            }
            await client.post(webhook_url, json=payload)
    except Exception as e:
        print(f"Error sending rejection webhook: {e}")

    # Cập nhật Webhook URL mặc định
    from app.models.setting import SystemSetting
    res_conf = await db.execute(select(SystemSetting).where(SystemSetting.key == "reject_webhook_url"))
    conf = res_conf.scalar_one_or_none()
    if not conf:
        new_conf = SystemSetting(key="reject_webhook_url", value=webhook_url)
        db.add(new_conf)
    elif conf.value != webhook_url:
        conf.value = webhook_url
        
    candidate.status = "từ chối"
    await db.commit()
    
    response = HTMLResponse("<script>window.location.reload();</script>")
    response.headers["HX-Refresh"] = "true"
    return response

from sqlalchemy import or_, func
import math

@router.get("", response_class=HTMLResponse)
async def list_candidates_ui(
    request: Request, 
    q: Optional[str] = None, 
    status: Optional[str] = None,
    job_id: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db)):
    
    stmt = select(Candidate).options(selectinload(Candidate.job).selectinload(Job.branch))
    
    # Text search
    if q:
        stmt = stmt.where(or_(
            Candidate.full_name.ilike(f"%{q}%"),
            Candidate.phone.ilike(f"%{q}%"),
            Candidate.email.ilike(f"%{q}%")
        ))
        
    # Status ASCII Mapping
    status_map = {
        "moi": "mới",
        "duyet": "duyệt",
        "tu-choi": "từ chối",
        "phong-van": "phỏng vấn",
        "gui-offer": "gửi offer",
        "da-tuyen": "đã tuyển"
    }

    # Dropdown filters
    if status:
        db_status = status_map.get(status, status)
        stmt = stmt.where(Candidate.status == db_status)
    if job_id and str(job_id).strip():
        try:
            stmt = stmt.where(Candidate.job_id == int(job_id))
        except ValueError:
            pass
        
    # Total count
    count_result = await db.execute(select(func.count()).select_from(stmt.with_only_columns(Candidate.id).subquery()))
    total = count_result.scalar_one()
    total_pages = math.ceil(total / size) if total > 0 else 1
    
    # Sorting
    _SORTABLE_FIELDS = {
        "full_name": Candidate.full_name,
        "status": Candidate.status,
        "created_at": Candidate.created_at,
        "score": Candidate.score,
    }
    sort_col = _SORTABLE_FIELDS.get(sort_by, Candidate.created_at)
    if sort_order.lower() == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())
        
    # Pagination
    stmt = stmt.offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    candidates = result.scalars().all()
    
    # Load jobs for filter dropdown
    job_res = await db.execute(select(Job).order_by(Job.title))
    jobs = job_res.scalars().all()
    
    # --- GLOBAL STATS FOR CARDS ---
    stats_stmt = select(
        func.count().label("total"),
        func.count().filter(Candidate.status == "đã tuyển").label("hired"),
        func.count().filter(Candidate.status == "phỏng vấn").label("interviewing")
    ).select_from(Candidate)
    stats_result = await db.execute(stats_stmt)
    stats = stats_result.one()
    
    context = {
        "request": request, 
        "candidates": candidates,
        "jobs": jobs,
        "total": total, # This is filtered total for pagination
        "total_candidates": stats.total, # Global total
        "hired_candidates": stats.hired,
        "interviewing_candidates": stats.interviewing,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "q": q or "",
        "status": status or "",
        "job_id": job_id or "",
        "sort_by": sort_by,
        "sort_order": sort_order
    }
    
    hx_target = request.headers.get("hx-target")
    if request.headers.get("hx-request") and hx_target == "candidates-list-container":
        return templates.TemplateResponse("candidates/partials/list_body.html", context)
        
    return templates.TemplateResponse("candidates/list.html", context)

@router.delete("/{candidate_id}", response_class=HTMLResponse)
async def delete_candidate_ui(request: Request, candidate_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_ui_permission("candidates", "delete"))):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    cand = result.scalar_one_or_none()
    if cand:
        await db.delete(cand)
        await db.commit()
    return HTMLResponse("")

@router.post("", response_class=HTMLResponse)
async def create_candidate_ui(
    request: Request,
    full_name: str = Form(None),
    job_id: Optional[str] = Form(None),
    webhook_url: str = Form(""),
    cv_file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("candidates", "create"))
):
    try:
        # Backend validation
        errors = []
        if not full_name: errors.append("Vui lòng nhập Họ tên")
        if not job_id: errors.append("Vui lòng chọn Vị trí ứng tuyển (sau khi chọn Chi nhánh)")
        if not cv_file or not cv_file.filename: errors.append("Vui lòng tải lên file CV")
        
        if errors:
            response = HTMLResponse(f'<div class="bg-red-50 text-red-600 p-4 rounded-lg mb-4 text-sm font-bold border border-red-100">' + '<br>'.join(errors) + '</div>', status_code=200)
            response.headers["HX-Retarget"] = "#form-error"
            response.headers["HX-Reswap"] = "innerHTML"
            return response
        
        actual_job_id = int(job_id)

        # Đảm bảo webhook_url có giá trị mặc định nếu rỗng
        if not webhook_url:
            res_conf = await db.execute(select(SystemSetting).where(SystemSetting.key == "candidate_webhook_url"))
            conf = res_conf.scalar_one_or_none()
            webhook_url = conf.value if conf else "https://n8n-auto.phucmeo.id.vn/webhook-test/danh-gia-ung-vien"

        # Lấy thông tin công việc kèm chi nhánh
        res_job = await db.execute(select(Job).options(selectinload(Job.branch)).where(Job.id == actual_job_id))
        job = res_job.scalar_one_or_none()
        job_title = job.title if job else "N/A"
        branch_name = job.branch.name if job and job.branch else "N/A"

        # 1. Chuyển tiếp tới Webhook
        if webhook_url and webhook_url.startswith("http"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    file_content = await cv_file.read()
                    # Webhook n8n thường nhận diện file qua key 'file' thay vì 'cv_file'
                    files = {'file': (cv_file.filename, file_content, cv_file.content_type)}
                    data = {
                        'full_name': full_name,
                        'job_title': job_title,
                        'branch_name': branch_name,
                        'source': 'SmartCV Auto UI',
                        'original_filename': cv_file.filename
                    }
                    # Gửi tới webhook
                    resp = await client.post(webhook_url, data=data, files=files)
                    
                    # Ghi log kết quả để gỡ lỗi nếu cần
                    with open("webhook_debug.log", "a", encoding="utf-8") as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()} - {webhook_url} - Status: {resp.status_code}\n")
                        
                # Cập nhật Webhook URL mặc định nếu có thay đổi
                res_conf = await db.execute(select(SystemSetting).where(SystemSetting.key == "candidate_webhook_url"))
                conf = res_conf.scalar_one_or_none()
                if not conf:
                    new_conf = SystemSetting(key="candidate_webhook_url", value=webhook_url)
                    db.add(new_conf)
                elif conf.value != webhook_url:
                    conf.value = webhook_url
                    
            except Exception as e:
                with open("webhook_debug.log", "a", encoding="utf-8") as f:
                    import datetime
                    f.write(f"{datetime.datetime.now()} - Webhook Error: {str(e)}\n")
                print(f"Lỗi Webhook hoặc Lưu cấu hình: {e}")
        else:
            with open("webhook_debug.log", "a", encoding="utf-8") as f:
                import datetime
                f.write(f"{datetime.datetime.now()} - Skip Webhook: URL invalid or empty ({webhook_url})\n")

        # 2. Không tạo bản ghi local theo yêu cầu của USER (Webhook sẽ gọi API tạo sau)
        await db.commit() # Để lưu cấu hình SystemSetting nếu có thay đổi
        
        return HTMLResponse("")
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        with open("webhook_debug.log", "a", encoding="utf-8") as f:
            f.write(f"SYSTEM FATAL ERROR in create_candidate_ui:\n{err_msg}\n====\n")
        response = HTMLResponse(f'<div class="bg-red-50 text-red-600 p-4 rounded-lg mb-4 text-sm font-bold border border-red-100">Lỗi Hệ thống: {str(e)}</div>', status_code=200)
        response.headers["HX-Retarget"] = "#form-error"
        response.headers["HX-Reswap"] = "innerHTML"
        return response
@router.post("/{candidate_id}/update", response_class=HTMLResponse)
async def update_candidate_ui(
    request: Request,
    candidate_id: int,
    full_name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    job_id: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    facebook: Optional[str] = Form(None),
    zalo: Optional[str] = Form(None),
    specific_address: Optional[str] = Form(None),
    cv_link: Optional[str] = Form(None),
    portfolio_link: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("candidates", "update"))
):
    res_cand = await db.execute(select(Candidate).options(selectinload(Candidate.job)).where(Candidate.id == candidate_id))
    cand = res_cand.scalar_one_or_none()
    if cand:
        actual_job_id = int(job_id) if job_id and str(job_id).isdigit() else None
        cand.full_name = full_name
        cand.email = email
        cand.phone = phone
        cand.job_id = actual_job_id
        
        if date_of_birth:
            from datetime import datetime
            try:
                cand.date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            except ValueError:
                pass
        else:
            cand.date_of_birth = None
            
        # Áp dụng gender trực tiếp từ form (đã chuẩn hóa male/female/other)
        if gender in ['male', 'female', 'other']:
            cand.gender = gender
        else:
            cand.gender = None
        cand.facebook = facebook
        cand.specific_address = specific_address
        cand.cv_link = cv_link
        cand.portfolio_link = portfolio_link
        
        await db.commit()
        await db.refresh(cand)
        
        res = await db.execute(select(Candidate).options(selectinload(Candidate.job).selectinload(Job.branch)).where(Candidate.id == cand.id))
        cand = res.scalar_one_or_none()

    return templates.TemplateResponse("candidates/row.html", {"request": request, "candidate": cand})
@router.post("/{candidate_id}/notes", response_class=HTMLResponse)
async def add_candidate_note_ui(
    request: Request,
    candidate_id: int,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("candidates", "update"))
):
    current_user = request.state.user
    new_note = CandidateNote(
        candidate_id=candidate_id,
        created_by=current_user.id,
        content=content
    )
    db.add(new_note)
    await db.commit()
    
    # Reload notes list
    result = await db.execute(
        select(CandidateNote)
        .options(selectinload(CandidateNote.author))
        .where(CandidateNote.candidate_id == candidate_id)
        .order_by(CandidateNote.created_at.desc())
    )
    notes = result.scalars().all()
    
    return templates.TemplateResponse("candidates/partials/note_list.html", {
        "request": request,
        "notes": notes,
        "candidate_id": candidate_id
    })

@router.get("/notes/{note_id}/edit", response_class=HTMLResponse)
async def edit_candidate_note_ui(
    request: Request,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("candidates", "update"))
):
    result = await db.execute(select(CandidateNote).where(CandidateNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi chú")
    
    return templates.TemplateResponse("candidates/partials/note_edit.html", {
        "request": request,
        "note": note
    })

@router.get("/notes/{note_id}/item", response_class=HTMLResponse)
async def get_candidate_note_item_ui(
    request: Request,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("candidates", "read"))
):
    result = await db.execute(
        select(CandidateNote)
        .options(selectinload(CandidateNote.author))
        .where(CandidateNote.id == note_id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi chú")
    
    return templates.TemplateResponse("candidates/partials/note_item.html", {
        "request": request,
        "note": note
    })

@router.post("/notes/{note_id}/update", response_class=HTMLResponse)
async def update_candidate_note_ui(
    request: Request,
    note_id: int,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("candidates", "update"))
):
    result = await db.execute(
        select(CandidateNote)
        .options(selectinload(CandidateNote.author))
        .where(CandidateNote.id == note_id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi chú")
    
    note.content = content
    # Cập nhật thời gian và người sửa mới nhất
    from datetime import datetime
    note.created_at = datetime.now()
    
    await db.commit()
    # Reload lại để lấy thông tin author mới nhất (vì người sửa đã thay đổi)
    result = await db.execute(
        select(CandidateNote)
        .options(selectinload(CandidateNote.author))
        .where(CandidateNote.id == note_id)
    )
    note = result.scalar_one()
    
    return templates.TemplateResponse("candidates/partials/note_item.html", {
        "request": request,
        "note": note
    })

@router.post("/notes/{note_id}/delete", response_class=HTMLResponse)
async def delete_candidate_note_ui(
    request: Request,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_ui_permission("candidates", "update"))
):
    result = await db.execute(select(CandidateNote).where(CandidateNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi chú")
    
    candidate_id = note.candidate_id
    await db.delete(note)
    await db.commit()
    
    # Return empty response with trigger to update count
    response = HTMLResponse(content="")
    response.headers["HX-Trigger"] = "noteDeleted"
    return response
