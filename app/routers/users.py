from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.security import get_password_hash
from app.deps import get_current_user, require_permission
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=PaginatedResponse[UserOut])
async def list_users(
    # ── Filters ──────────────────────────────────────────────
    q:         Optional[str]  = Query(None,  description="Tìm kiếm theo tên hoặc email"),
    role:      Optional[str]  = Query(None,  description="Lọc theo vai trò (admin, hr_staff, interviewer...)"),
    is_active: Optional[bool] = Query(None,  description="Lọc theo trạng thái hoạt động"),
    # ── Sorting ───────────────────────────────────────────────
    sort_by:    str = Query("id",   description="Trường sắp xếp: id | full_name | created_at"),
    sort_order: str = Query("asc",  description="asc | desc"),
    # ── Pagination ────────────────────────────────────────────
    page: int        = Query(1,  ge=1,        description="Trang hiện tại"),
    size: int        = Query(20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    db: AsyncSession = Depends(get_db),
    _: User          = Depends(require_permission("users", "read")),
):
    _SORTABLE = {"id": User.id, "full_name": User.full_name, "created_at": User.created_at}

    query = select(User)

    # Filters
    if q:
        keyword = f"%{q.strip()}%"
        query = query.where(
            or_(User.full_name.ilike(keyword), User.email.ilike(keyword))
        )
    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Count total
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    # Sorting
    sort_col = _SORTABLE.get(sort_by, User.id)
    query = query.order_by(sort_col.asc() if sort_order.lower() == "asc" else sort_col.desc())

    # Pagination
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    return PaginatedResponse(total=total, page=page, size=size, items=result.scalars().all())


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users", "create")),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email đã tồn tại")
    user = User(
        full_name=body.full_name,
        email=body.email,
        password_hash=get_password_hash(body.password),
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    return user


@router.post("/{user_id}/update", response_model=UserOut)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users", "update")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")

    updates = body.model_dump(exclude_unset=True)

    # Xử lý password riêng (cần hash)
    password = updates.pop("password", None)
    for field, val in updates.items():
        setattr(user, field, val)
    if password is not None:
        user.password_hash = get_password_hash(password)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users", "delete")),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Không thể xóa chính mình")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    user.is_active = False  # Soft deactivate
    await db.commit()
