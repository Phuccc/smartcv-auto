from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.deps import require_permission
from app.models.setting import SystemSetting
from app.models.user import User
from app.schemas.setting import SystemSettingOut, SystemSettingUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("", response_model=List[SystemSettingOut], summary="Danh sách cài đặt hệ thống")
async def list_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("roles", "read")), # Dùng tạm permission của roles cho settings
):
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
    return result.scalars().all()

@router.get("/{key}", response_model=SystemSettingOut, summary="Chi tiết cài đặt theo key")
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("roles", "read")),
):
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Không tìm thấy cài đặt")
    return setting

@router.post("/{key}", response_model=SystemSettingOut, summary="Cập nhật cài đặt hệ thống")
async def update_setting(
    key: str,
    body: SystemSettingUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("roles", "update")),
):
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = body.value
    else:
        setting = SystemSetting(key=key, value=body.value)
        db.add(setting)
    
    await db.commit()
    await db.refresh(setting)
    return setting
