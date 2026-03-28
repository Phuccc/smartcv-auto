from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.deps import NotAuthenticatedException, NotAuthorizedException
from app.models.user import User
from app.models.interview import Interview
from sqlalchemy import select, update
import asyncio
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── API Routers ────────────────────────────────────────────────────────────
from app.routers.auth        import router as auth_router
from app.routers.users       import router as users_router
from app.routers.roles       import router as roles_router
from app.routers.departments import depts_router, skills_router
from app.routers.branches    import router as branches_router
from app.routers.jobs        import router as jobs_router
from app.routers.candidates  import router as candidates_router
from app.routers.interviews  import router as interviews_router
from app.routers.settings    import router as settings_router

# ── UI Routers (ẩn khỏi Swagger) ──────────────────────────────────────────
from app.routers.ui_auth       import router as ui_auth_router
from app.routers.ui_dashboard  import router as ui_dashboard_router
from app.routers.ui_jobs       import router as ui_jobs_router
from app.routers.ui_candidates import router as ui_candidates_router
from app.routers.ui_interviews import router as ui_interviews_router
from app.routers.ui_users      import router as ui_users_router
from app.routers.ui_settings   import router as ui_settings_router
from app.routers.ui_categories import router as ui_categories_router

import os

app = FastAPI(
    title="SmartCV Auto — HR Recruitment API",
    description="Backend API cho hệ thống tuyển dụng nội bộ SmartCV Auto.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Exception Handlers ─────────────────────────────────────────────────────
@app.exception_handler(NotAuthenticatedException)
async def auth_exception_handler(request: Request, exc: NotAuthenticatedException):
    return RedirectResponse(url="/ui/auth/login", status_code=303)


@app.exception_handler(NotAuthorizedException)
async def authz_exception_handler(request: Request, exc: NotAuthorizedException):
    return RedirectResponse(url="/ui/dashboard?error=forbidden", status_code=303)


# ── UI Auth Middleware ─────────────────────────────────────────────────────
class UIAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/ui/") and not path.startswith("/ui/auth/"):
            token = request.cookies.get("access_token")
            if not token:
                return RedirectResponse(url="/ui/auth/login", status_code=303)
            payload = decode_token(token)
            if not payload or not payload.get("sub"):
                return RedirectResponse(url="/ui/auth/login", status_code=303)
            user_id = int(payload["sub"])
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
            if not user or not user.is_active:
                return RedirectResponse(url="/ui/auth/login", status_code=303)
            request.state.user = user
        return await call_next(request)


app.add_middleware(UIAuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static Files ───────────────────────────────────────────────────────────
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── API Routes (/api/v1) ───────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth_router,       prefix=PREFIX)
app.include_router(users_router,      prefix=PREFIX)
app.include_router(roles_router,      prefix=PREFIX)
app.include_router(depts_router,      prefix=PREFIX)
app.include_router(skills_router,     prefix=PREFIX)
app.include_router(branches_router,   prefix=PREFIX)
app.include_router(jobs_router,       prefix=PREFIX)
app.include_router(candidates_router, prefix=PREFIX)
app.include_router(interviews_router, prefix=PREFIX)
app.include_router(settings_router,   prefix=PREFIX)

# ── UI Routes (ẩn khỏi Swagger — dùng cookie, không test bằng Swagger) ────
app.include_router(ui_auth_router,       include_in_schema=False)
app.include_router(ui_dashboard_router,  include_in_schema=False)
app.include_router(ui_jobs_router,       include_in_schema=False)
app.include_router(ui_candidates_router, include_in_schema=False)
app.include_router(ui_interviews_router, include_in_schema=False)
app.include_router(ui_users_router,      include_in_schema=False)
app.include_router(ui_settings_router,   include_in_schema=False)
app.include_router(ui_categories_router, include_in_schema=False)


# ── Health Check ───────────────────────────────────────────────────────────
@app.get("/", tags=["root"], include_in_schema=False)
async def root():
    return RedirectResponse(url="/ui/auth/login")


@app.get("/health", tags=["root"])
async def health():
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return HTMLResponse(status_code=204)


# ── Background Task: Tự động hoàn thành phỏng vấn ────────────────────────────
async def auto_complete_interviews():
    """Vòng lặp chạy mỗi 5 phút để cập nhật trạng thái phỏng vấn đã kết thúc."""
    while True:
        try:
            async with AsyncSessionLocal() as session:
                now = datetime.now()
                stmt = (
                    update(Interview)
                    .where(Interview.status == "scheduled")
                    .where(Interview.end_at < now)
                    .values(status="completed")
                )
                result = await session.execute(stmt)
                await session.commit()
                if result.rowcount > 0:
                    logger.info(f"Auto-completed {result.rowcount} interviews.")
        except Exception as e:
            logger.error(f"Error in auto_complete_interviews: {e}")
        
        await asyncio.sleep(300)  # Chạy mỗi 5 phút


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(auto_complete_interviews())

