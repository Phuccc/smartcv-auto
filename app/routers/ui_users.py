from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from app.core.templates import templates
from typing import Optional

from app.deps import get_db, require_ui_permission
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.models.user import User, RolePermission, Role
from app.core.security import get_password_hash

router = APIRouter(
    prefix="/ui/users",
    tags=["UI Users"],
    dependencies=[Depends(require_ui_permission("users", "read"))]
)

# Danh sách các tài nguyên trong hệ thống để phân quyền
RESOURCES = ['candidates', 'jobs', 'interviews', 'users', 'departments', 'skills', 'branches']

# ── DANH SÁCH USERS & ROLES ────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def list_users_ui(
    request: Request, 
    tab: str = "users", 
    q: Optional[str] = None, 
    role: Optional[str] = None,
    is_active: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    size: int = 15,
    db: AsyncSession = Depends(get_db)):
    if tab == "roles":
        # Lấy từ bảng roles (có is_system, display_name)
        stmt = select(Role).order_by(Role.is_system.desc(), Role.name)
        res = await db.execute(stmt)
        role_objs = res.scalars().all()

        role_stats = []
        for r in role_objs:
            cnt = await db.execute(select(func.count(User.id)).where(User.role == r.name))
            role_stats.append({
                "name": r.name,
                "display_name": r.display_name,
                "is_system": r.is_system,
                "user_count": cnt.scalar(),
            })

        return templates.TemplateResponse("roles/list.html", {
            "request": request,
            "roles": role_stats,
            "tab": tab
        })

    # Users tab
    stmt = select(User)
    
    if q:
        stmt = stmt.where(User.full_name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
        
    if role:
        stmt = stmt.where(User.role == role)
        
    if is_active and str(is_active).strip():
        is_active_val = str(is_active).lower() == 'true'
        stmt = stmt.where(User.is_active == is_active_val)
        
    count_result = await db.execute(select(func.count()).select_from(stmt.with_only_columns(User.id).subquery()))
    total = count_result.scalar_one()
    
    import math
    total_pages = math.ceil(total / size) if total > 0 else 1
    
    # Sorting
    _SORTABLE_FIELDS = {
        "full_name": User.full_name,
        "role": User.role,
        "is_active": User.is_active,
        "created_at": User.created_at,
    }
    sort_col = _SORTABLE_FIELDS.get(sort_by, User.created_at)
    if sort_order.lower() == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())

    stmt = stmt.offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    # Query summary counts (Total active/inactive for UI)
    act_res = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    inact_res = await db.execute(select(func.count(User.id)).where(User.is_active == False))
    count_act = act_res.scalar_one()
    count_inact = inact_res.scalar_one()
    total_user_count = count_act + count_inact

    role_res = await db.execute(select(Role))
    roles_dict = {r.name: r for r in role_res.scalars().all()}

    context = {
        "request": request, 
        "users": users, 
        "roles_dict": roles_dict, 
        "tab": tab,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "q": q or "",
        "role": role or "",
        "is_active": is_active or "",
        "sort_by": sort_by,
        "sort_order": sort_order,
        "total_user_count": total_user_count,
        "active_count": count_act,
        "inactive_count": count_inact
    }

    hx_target = request.headers.get("hx-target")
    if request.headers.get("hx-request") and hx_target == "users-list-container":
        return templates.TemplateResponse("users/partials/list_body.html", context)

    return templates.TemplateResponse("users/list.html", context)


@router.delete("/{user_id}", response_class=HTMLResponse)
async def delete_user_ui(request: Request, user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await db.delete(user)
        await db.commit()
    return HTMLResponse("")


@router.get("/form", response_class=HTMLResponse)
async def new_user_form(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Role).order_by(Role.is_system.desc(), Role.name))
    roles = result.scalars().all()
    if not roles:
        # Fallback
        roles = [{"name": "admin", "display_name": "Quản trị viên"},
                 {"name": "hr_staff", "display_name": "Chuyên viên Nhân sự"},
                 {"name": "interviewer", "display_name": "Người phỏng vấn"}]
    return templates.TemplateResponse("users/form.html", {"request": request, "user": None, "roles": roles})


@router.get("/form/{user_id}", response_class=HTMLResponse)
async def edit_user_form(request: Request, user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    res_roles = await db.execute(select(Role).order_by(Role.is_system.desc(), Role.name))
    roles = res_roles.scalars().all()

    return templates.TemplateResponse("users/form.html", {"request": request, "user": user, "roles": roles})


@router.post("", response_class=HTMLResponse)
async def create_user_ui(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("hr_staff"),
    is_active: bool = Form(default=False),
    db: AsyncSession = Depends(get_db)
):
    hashed = get_password_hash(password)
    new_user = User(full_name=full_name, email=email, password_hash=hashed, role=role, is_active=is_active)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    role_res = await db.execute(select(Role))
    roles_dict = {r.name: r for r in role_res.scalars().all()}
    
    return templates.TemplateResponse("users/row.html", {"request": request, "user": new_user, "roles_dict": roles_dict, "loop_index": 0})


@router.post("/{user_id}/update", response_class=HTMLResponse)
async def update_user_ui(
    request: Request,
    user_id: int,
    full_name: str = Form(...),
    email: str = Form(...),
    password: Optional[str] = Form(None),
    role: str = Form("hr_staff"),
    is_active: bool = Form(default=False),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.full_name = full_name
        user.email = email
        if password:
            user.password_hash = get_password_hash(password)
        user.role = role
        user.is_active = is_active
        await db.commit()
        await db.refresh(user)
        
    role_res = await db.execute(select(Role))
    roles_dict = {r.name: r for r in role_res.scalars().all()}
    
    return templates.TemplateResponse("users/row.html", {"request": request, "user": user, "roles_dict": roles_dict, "loop_index": 0})


# ── ROLES ──────────────────────────────────────────────────────────────────

@router.get("/roles/form", response_class=HTMLResponse)
async def new_role_form(request: Request):
    return templates.TemplateResponse("roles/form.html", {
        "request": request,
        "role_name": "",
        "display_name": "",
        "is_system": False,
        "permissions": {},
        "resources": RESOURCES
    })


@router.get("/roles/form/{role_name}", response_class=HTMLResponse)
async def edit_role_form(request: Request, role_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RolePermission).where(RolePermission.role == role_name))
    perms = result.scalars().all()
    perm_dict = {p.resource: p for p in perms}

    role_obj_res = await db.execute(select(Role).where(Role.name == role_name))
    role_obj = role_obj_res.scalar_one_or_none()

    return templates.TemplateResponse("roles/form.html", {
        "request": request,
        "role_name": role_name,
        "display_name": role_obj.display_name if role_obj else role_name,
        "is_system": role_obj.is_system if role_obj else False,
        "permissions": perm_dict,
        "resources": RESOURCES
    })


@router.post("/roles", response_class=HTMLResponse)
async def save_role_ui(request: Request, db: AsyncSession = Depends(get_db)):
    form_data = await request.form()
    role_name = (form_data.get("role_name") or "").strip()
    display_name = (form_data.get("display_name") or role_name).strip()

    if not role_name:
        return HTMLResponse("<p class='text-red-500'>Tên vai trò không được trống.</p>", status_code=400)

    # Upsert bảng roles
    existing = await db.execute(select(Role).where(Role.name == role_name))
    role_obj = existing.scalar_one_or_none()
    if role_obj is None:
        role_obj = Role(name=role_name, display_name=display_name, is_system=False)
        db.add(role_obj)
    else:
        # Chỉ cập nhật display_name (không thay đổi is_system)
        role_obj.display_name = display_name

    await db.flush()

    # Xóa và tạo lại permissions
    await db.execute(delete(RolePermission).where(RolePermission.role == role_name))

    for res in RESOURCES:
        can_create = form_data.get(f"{res}_create") == "on"
        can_read   = form_data.get(f"{res}_read")   == "on"
        can_update = form_data.get(f"{res}_update") == "on"
        can_delete = form_data.get(f"{res}_delete") == "on"

        if can_create or can_read or can_update or can_delete:
            db.add(RolePermission(
                role=role_name, resource=res,
                can_create=can_create, can_read=can_read,
                can_update=can_update, can_delete=can_delete
            ))

    await db.commit()
    return HTMLResponse(content="", headers={"HX-Refresh": "true"})


@router.delete("/roles/{role_name}", response_class=HTMLResponse)
async def delete_role_ui(request: Request, role_name: str, db: AsyncSession = Depends(get_db)):
    # Không cho xóa vai trò hệ thống
    role_obj_res = await db.execute(select(Role).where(Role.name == role_name))
    role_obj = role_obj_res.scalar_one_or_none()
    if role_obj and role_obj.is_system:
        return HTMLResponse(
            "<div class='text-red-500 text-sm'>Không thể xóa vai trò hệ thống.</div>",
            status_code=403
        )

    await db.execute(delete(RolePermission).where(RolePermission.role == role_name))
    if role_obj:
        await db.delete(role_obj)
    await db.commit()
    return HTMLResponse("")
