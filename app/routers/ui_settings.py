from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from typing import Optional
import os
import uuid
from pathlib import Path
import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.templates import templates
from app.deps import require_ui_role, get_current_user_ui
from app.models.user import User
from app.core.security import verify_password, get_password_hash

router = APIRouter(
    prefix="/ui/settings",
    tags=["UI Settings"]
)

@router.post("/update-profile", response_class=HTMLResponse)
async def update_profile(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    role: Optional[str] = Form(None),
    user: User = Depends(get_current_user_ui),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates user profile information. 
    Email and Full Name can be updated by any user.
    Role can only be updated by Admin.
    """
    user.full_name = full_name
    user.email = email
    
    # Chỉ Admin mới được phép thay đổi role
    if role and role != user.role:
        if user.role == "admin":
            user.role = role
        else:
            # Nếu không phải admin mà gửi role khác lên -> Báo lỗi hoặc lờ đi (ở đây chọn báo lỗi nhẹ)
            return HTMLResponse(content="""
                <div class="p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-xs font-bold flex items-center gap-2 mb-4 animate-shake">
                    <span class="material-symbols-outlined text-sm">error</span>
                    Bạn không có quyền thay đổi vai trò.
                </div>
            """, status_code=200)

    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        return HTMLResponse(content=f"""
            <div class="p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-xs font-bold flex items-center gap-2 mb-4 animate-shake">
                <span class="material-symbols-outlined text-sm">error</span>
                Lỗi cập nhật: {str(e)}
            </div>
        """, status_code=200)

    return HTMLResponse(content="""
        <div class="p-3 bg-green-50 border border-green-200 text-green-600 rounded-lg text-xs font-bold flex items-center gap-2 mb-4 animate-fade-in">
            <span class="material-symbols-outlined text-sm">check_circle</span>
            Cập nhật thông tin thành công!
        </div>
    """)

@router.get("", response_class=HTMLResponse)
async def settings_page(
    request: Request, 
    tab: str = "general",
    user: User = Depends(get_current_user_ui),
    db: AsyncSession = Depends(get_db)
):
    """
    Renders the settings page with user data and tab awareness.
    """
    from app.models.user import Role
    stmt = select(Role).order_by(Role.is_system.desc(), Role.name)
    res = await db.execute(stmt)
    roles = res.scalars().all()

    return templates.TemplateResponse("settings/index.html", {
        "request": request,
        "user_data": user,
        "tab": tab,
        "roles": roles
    })


@router.post("/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user: User = Depends(get_current_user_ui),
    db: AsyncSession = Depends(get_db)
):
    """
    Handles password change request via HTMX.
    """
    # 1. Kiểm tra mật khẩu cũ
    if not verify_password(current_password, user.password_hash):
        return HTMLResponse(content="""
            <div class="p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-xs font-bold flex items-center gap-2 mb-4 animate-shake">
                <span class="material-symbols-outlined text-sm">error</span>
                Mật khẩu hiện tại không chính xác.
            </div>
        """, status_code=200)

    # 2. Kiểm tra mật khẩu mới khớp nhau
    if new_password != confirm_password:
        return HTMLResponse(content="""
            <div class="p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-xs font-bold flex items-center gap-2 mb-4 animate-shake">
                <span class="material-symbols-outlined text-sm">error</span>
                Xác nhận mật khẩu mới không khớp.
            </div>
        """, status_code=200)
    
    # 3. Độ dài tối thiểu
    if len(new_password) < 6:
        return HTMLResponse(content="""
            <div class="p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-xs font-bold flex items-center gap-2 mb-4 animate-shake">
                <span class="material-symbols-outlined text-sm">error</span>
                Mật khẩu phải có ít nhất 6 ký tự.
            </div>
        """, status_code=200)

    # 4. Cập nhật
    user.password_hash = get_password_hash(new_password)
    await db.commit()

    return HTMLResponse(content="""
        <div class="p-3 bg-green-50 border border-green-200 text-green-600 rounded-lg text-xs font-bold flex items-center gap-2 mb-4 animate-fade-in">
            <span class="material-symbols-outlined text-sm">check_circle</span>
            Đã thay đổi mật khẩu thành công!
        </div>
        <script>
            // Xóa nội dung các ô nhập sau khi thành công
            document.querySelectorAll('input[type="password"]').forEach(i => i.value = '');
        </script>
    """)


@router.post("/generate-api-key", response_class=HTMLResponse)
async def generate_api_key(
    request: Request,
    user: User = Depends(get_current_user_ui),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a new API key for the user.
    """
    new_key = f"sk-{secrets.token_urlsafe(32)}"
    user.api_key = new_key
    await db.commit()
    
    # Trả về partial để HTMX cập nhật input (khớp với index.html mới)
    return HTMLResponse(content=f"""
        <div id="api-key-container" class="space-y-4 animate-fade-in">
            <div class="space-y-2">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest text-green-600">Mã API vừa tạo (Hãy lưu lại ngay!)</label>
                <div class="flex items-center gap-2">
                    <input type="text" readonly value="{new_key}" 
                           class="block w-full rounded-xl border-green-200 bg-green-50/30 text-sm font-mono text-green-700 dark:bg-green-900/10 dark:border-green-900/30" />
                    <button hx-post="/ui/settings/generate-api-key" hx-target="#api-key-container" hx-swap="outerHTML" hx-confirm="Mã hiện tại sẽ bị hủy. Xác nhận cấp lại mã mới?"
                            class="px-5 py-2.5 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition-all shrink-0 flex items-center gap-2">
                        <span class="material-symbols-outlined text-sm">refresh</span>
                        Làm mới
                    </button>
                </div>
                <p class="text-[10px] text-green-600 font-bold flex items-center gap-1">
                    <span class="material-symbols-outlined text-xs">check_circle</span>
                    Đã tạo mã mới thành công!
                </p>
            </div>
        </div>
    """)


@router.post("/upload-avatar", response_class=HTMLResponse)
async def upload_avatar(
    request: Request,
    avatar: UploadFile = File(...),
    user: User = Depends(get_current_user_ui),
    db: AsyncSession = Depends(get_db)
):
    """
    Handles avatar upload via HTMX.
    """
    # 1. Kiểm tra định dạng
    ext = os.path.splitext(avatar.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        return HTMLResponse(content=f"""
            <script>
                alert('Định dạng file {ext} không hỗ trợ. Hãy chọn ảnh JPG, PNG, WEBP hoặc GIF.');
            </script>
        """, status_code=200)

    # 2. Tạo đường dẫn và tên file duy nhất
    upload_dir = Path("app/static/avatars")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_name = f"avatar_{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = upload_dir / file_name
    
    # 3. Lưu file
    content = await avatar.read()
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # 4. Cập nhật DB
    # Xóa ảnh cũ nếu có (tùy chọn, để tiết kiệm dung lượng)
    if user.avatar_url and user.avatar_url.startswith("/static/avatars/"):
        old_path = Path("app" + user.avatar_url)
        if old_path.exists():
            try:
                os.remove(old_path)
            except: pass

    user.avatar_url = f"/static/avatars/{file_name}"
    await db.commit()

    # 5. Trả về partial để cập nhật giao diện (Avatar img tag)
    return HTMLResponse(content=f"""
        <div class="relative group" id="avatar-display-container">
            <img alt="Avatar" id="user-avatar" 
                 class="w-24 h-24 rounded-full border-4 border-white dark:border-slate-800 shadow-sm object-cover" 
                 src="{user.avatar_url}"/>
            <button type="button" onclick="document.getElementById('avatar-input').click()"
                    class="absolute bottom-0 right-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center shadow-lg hover:scale-110 transition-transform">
                <span class="material-symbols-outlined text-lg">edit</span>
            </button>
        </div>
        <script>
            console.log('Avatar updated');
        </script>
    """)
