from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete

from app.core.database import get_db
from app.deps import require_role
from app.models.user import Role, RolePermission
from app.schemas.user import (
    RoleOut, RoleCreate, RoleUpdate,
    RolePermissionItem, RoleDetailOut,
)

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=List[RoleOut])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin", "hr_staff")),
):
    """Danh sách tất cả vai trò."""
    result = await db.execute(select(Role).order_by(Role.is_system.desc(), Role.name))
    return result.scalars().all()


@router.post("", response_model=RoleOut, status_code=201)
async def create_role(
    body: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """Tạo vai trò mới (không trùng name)."""
    existing = await db.execute(select(Role).where(Role.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tên vai trò đã tồn tại")
    role = Role(name=body.name, display_name=body.display_name, is_system=False)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


@router.get("/{role_name}", response_model=RoleDetailOut)
async def get_role(
    role_name: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """Chi tiết vai trò kèm danh sách permissions."""
    result = await db.execute(select(Role).where(Role.name == role_name))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Không tìm thấy vai trò")

    perm_result = await db.execute(select(RolePermission).where(RolePermission.role == role_name))
    perms = perm_result.scalars().all()

    return RoleDetailOut(
        name=role.name,
        display_name=role.display_name,
        is_system=role.is_system,
        permissions=[
            RolePermissionItem(
                resource=p.resource,
                can_create=p.can_create,
                can_read=p.can_read,
                can_update=p.can_update,
                can_delete=p.can_delete,
            )
            for p in perms
        ],
    )


@router.post("/{role_name}/update", response_model=RoleOut)
async def update_role(
    role_name: str,
    body: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """Cập nhật display_name của vai trò (không đổi được name và is_system)."""
    result = await db.execute(select(Role).where(Role.name == role_name))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Không tìm thấy vai trò")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(role, field, val)
    await db.commit()
    await db.refresh(role)
    return role


@router.delete("/{role_name}", status_code=204)
async def delete_role(
    role_name: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """Xóa vai trò tùy chỉnh (không xóa được is_system=True)."""
    result = await db.execute(select(Role).where(Role.name == role_name))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Không tìm thấy vai trò")
    if role.is_system:
        raise HTTPException(status_code=403, detail="Không thể xóa vai trò hệ thống")
    await db.execute(sa_delete(RolePermission).where(RolePermission.role == role_name))
    await db.delete(role)
    await db.commit()


@router.post("/{role_name}/permissions", response_model=List[RolePermissionItem])
async def set_permissions(
    role_name: str,
    permissions: List[RolePermissionItem],
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """Ghi đè toàn bộ permissions của vai trò."""
    result = await db.execute(select(Role).where(Role.name == role_name))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Không tìm thấy vai trò")

    await db.execute(sa_delete(RolePermission).where(RolePermission.role == role_name))
    for p in permissions:
        db.add(RolePermission(
            role=role_name,
            resource=p.resource,
            can_create=p.can_create,
            can_read=p.can_read,
            can_update=p.can_update,
            can_delete=p.can_delete,
        ))
    await db.commit()
    return permissions
