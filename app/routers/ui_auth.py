from fastapi import APIRouter, Request, Depends, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User

router = APIRouter(prefix="/ui/auth", tags=["UI Auth"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "error": error
    })

@router.post("/login")
async def process_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False),
    db: AsyncSession = Depends(get_db)
):
    # Retrieve user
    result = await db.execute(select(User).where(User.email == username))
    user = result.scalar_one_or_none()
    
    # Verify credentials
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Email hoặc mật khẩu không chính xác."
        })
        
    if not user.is_active:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Tài khoản của bạn đã bị vô hiệu hóa."
        })
    
    # Generate token
    token = create_access_token({"sub": str(user.id), "role": user.role})
    
    # Create redirect response to dashboard
    response = RedirectResponse(url="/ui/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    
    # Set HttpOnly cookie
    max_age = 30 * 24 * 60 * 60 if remember else 24 * 60 * 60 # 30 days or 1 day
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=max_age,
        expires=max_age,
        samesite="lax",
        secure=False, # Set True in production (HTTPS)
    )
    
    return response

@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/ui/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response
