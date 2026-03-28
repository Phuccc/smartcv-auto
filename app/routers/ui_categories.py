from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.templates import templates
from app.deps import require_ui_permission
from app.models.department import Department, Skill, Branch
from typing import Literal

router = APIRouter(
    prefix="/ui/categories",
    tags=["UI Categories"]
)

MODEL_MAP = {
    "branches": Branch,
    "skills": Skill,
    "departments": Department
}

TITLE_MAP = {
    "branches": "Chi nhánh",
    "skills": "Kỹ năng",
    "departments": "Phòng ban"
}

@router.get("", response_class=HTMLResponse)
async def categories_page(
    request: Request, 
    tab: str = "branches", 
    q: str = "",
    db: AsyncSession = Depends(get_db)
):
    if tab not in MODEL_MAP:
        tab = "branches"
    
    # Check permission for the specific tab
    await require_ui_permission(tab, "read")(request, db)
    if tab not in MODEL_MAP:
        tab = "branches"
    
    model = MODEL_MAP[tab]
    stmt = select(model).order_by(model.created_at.desc())
    if q:
        stmt = stmt.where(model.name.ilike(f"%{q}%"))
        
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return templates.TemplateResponse("settings/categories.html", {
        "request": request,
        "items": items,
        "category_type": tab,
        "q": q,
        "title": TITLE_MAP[tab]
    })

@router.get("/{category_type}", response_class=HTMLResponse)
async def list_categories_partial(
    request: Request, 
    category_type: str, 
    q: str = "",
    db: AsyncSession = Depends(get_db)
):
    if category_type not in MODEL_MAP:
        return HTMLResponse("Invalid type", status_code=400)
    
    # Check permission
    await require_ui_permission(category_type, "read")(request, db)
    if category_type not in MODEL_MAP:
        return HTMLResponse("Invalid type", status_code=400)
    
    model = MODEL_MAP[category_type]
    stmt = select(model).order_by(model.created_at.desc())
    if q:
        stmt = stmt.where(model.name.ilike(f"%{q}%"))
        
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    # Check if this is an HTMX search request
    hx_target = request.headers.get("HX-Target")
    if hx_target == "category-grid-body":
        return templates.TemplateResponse("settings/partials/category_grid.html", {
            "request": request,
            "items": items,
            "category_type": category_type,
            "q": q,
            "title": TITLE_MAP[category_type]
        })

    return templates.TemplateResponse("settings/partials/category_list.html", {
        "request": request,
        "items": items,
        "category_type": category_type,
        "q": q,
        "title": TITLE_MAP[category_type]
    })

@router.post("/{category_type}", response_class=HTMLResponse)
async def create_category(
    request: Request, 
    category_type: str, 
    name: str = Form(...), 
    db: AsyncSession = Depends(get_db)
):
    if category_type not in MODEL_MAP:
        return HTMLResponse("Invalid type", status_code=400)
    
    # Check permission
    await require_ui_permission(category_type, "create")(request, db)
    if category_type not in MODEL_MAP:
        return HTMLResponse("Invalid type", status_code=400)
    
    model = MODEL_MAP[category_type]
    
    # Check if exists
    existing = await db.execute(select(model).where(model.name == name))
    if existing.scalar_one_or_none():
        # Trả về error message nhỏ nếu trùng (tùy biến sau)
        pass

    new_item = model(name=name)
    db.add(new_item)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        return HTMLResponse(f"Lỗi: {str(e)}", status_code=400)
        
    # Trả về toàn bộ list partial để refresh
    stmt = select(model).order_by(model.created_at.desc())
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return templates.TemplateResponse("settings/partials/category_list.html", {
        "request": request,
        "items": items,
        "category_type": category_type,
        "title": TITLE_MAP[category_type]
    })

@router.post("/{category_type}/{item_id}/update", response_class=HTMLResponse)
async def update_category(
    request: Request,
    category_type: str,
    item_id: int,
    name: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    if category_type not in MODEL_MAP:
        return HTMLResponse("Invalid type", status_code=400)
    
    # Check permission
    await require_ui_permission(category_type, "update")(request, db)
    if category_type not in MODEL_MAP:
        return HTMLResponse("Invalid type", status_code=400)
    
    model = MODEL_MAP[category_type]
    stmt = select(model).where(model.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    
    if not item:
        return HTMLResponse("Not found", status_code=404)
    
    item.name = name
    await db.commit()
    
    return templates.TemplateResponse("settings/partials/category_row.html", {
        "request": request,
        "item": item,
        "category_type": category_type
    })

# Helper route để lấy form edit inline
@router.get("/{category_type}/{item_id}/edit", response_class=HTMLResponse)
async def get_edit_row(
    request: Request, 
    category_type: str, 
    item_id: int, 
    db: AsyncSession = Depends(get_db)
):
    # Check permission
    await require_ui_permission(category_type, "update")(request, db)
    model = MODEL_MAP.get(category_type)
    if not model: return HTMLResponse("Error", status_code=400)
    
    stmt = select(model).where(model.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    
    return templates.TemplateResponse("settings/partials/category_row.html", {
        "request": request,
        "item": item,
        "category_type": category_type,
        "editing": True
    })

@router.get("/{category_type}/{item_id}/cancel", response_class=HTMLResponse)
async def cancel_edit_row(
    request: Request, 
    category_type: str, 
    item_id: int, 
    db: AsyncSession = Depends(get_db)
):
    # Check permission
    await require_ui_permission(category_type, "read")(request, db)
    model = MODEL_MAP.get(category_type)
    stmt = select(model).where(model.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    
    return templates.TemplateResponse("settings/partials/category_row.html", {
        "request": request,
        "item": item,
        "category_type": category_type,
        "editing": False
    })

@router.delete("/{category_type}/{item_id}", response_class=HTMLResponse)
async def delete_category(
    request: Request,
    category_type: str,
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    if category_type not in MODEL_MAP:
        return HTMLResponse("Invalid type", status_code=400)
    
    # Check permission
    await require_ui_permission(category_type, "delete")(request, db)
    if category_type not in MODEL_MAP:
        return HTMLResponse("Invalid type", status_code=400)
    
    model = MODEL_MAP[category_type]
    stmt = select(model).where(model.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    
    if item:
        try:
            await db.delete(item)
            await db.commit()
        except Exception:
            await db.rollback()
            return HTMLResponse("<script>alert('Không thể xóa vì mục này đang được sử dụng!');</script>", status_code=200)

    return HTMLResponse(content="")
