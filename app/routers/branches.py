from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.deps import require_permission
from app.models.department import Branch
from app.models.user import User
from app.schemas.branch import BranchCreate, BranchUpdate, BranchOut

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("", response_model=List[BranchOut], summary="Danh sách chi nhánh công ty")
async def list_branches(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("departments", "read")),
):
    result = await db.execute(select(Branch).order_by(Branch.name))
    return result.scalars().all()


@router.get("/{branch_id}", response_model=BranchOut, summary="Chi tiết chi nhánh")
async def get_branch(
    branch_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("departments", "read")),
):
    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=404, detail="Không tìm thấy chi nhánh")
    return branch


@router.post("", response_model=BranchOut, status_code=201, summary="Thêm chi nhánh mới")
async def create_branch(
    body: BranchCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("departments", "create")),
):
    branch = Branch(name=body.name)
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch


@router.post("/{branch_id}/update", response_model=BranchOut, summary="Sửa tên chi nhánh")
async def update_branch(
    branch_id: int,
    body: BranchUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("departments", "update")),
):
    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=404, detail="Không tìm thấy chi nhánh")
    branch.name = body.name
    await db.commit()
    await db.refresh(branch)
    return branch


@router.delete("/{branch_id}", status_code=204, summary="Xóa chi nhánh")
async def delete_branch(
    branch_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("departments", "delete")),
):
    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=404, detail="Không tìm thấy chi nhánh")
    await db.delete(branch)
    await db.commit()
