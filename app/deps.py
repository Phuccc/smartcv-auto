from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, RolePermission

security_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# ── Tái sử dụng get_db từ database.py ─────────────────────────────────────
# (re-export để import từ 1 chỗ)


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    api_key: Annotated[Optional[str], Depends(api_key_header)] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Thông tin xác thực không hợp lệ",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Ưu tiên kiểm tra API Key (cố định)
    if api_key:
        result = await db.execute(select(User).where(User.api_key == api_key))
        user = result.scalar_one_or_none()
        if user and user.is_active:
            return user
        raise exc

    # Kiểm tra JWT Token (thời hạn)
    token = auth.credentials if auth else None
    if not token:
        raise exc
        
    payload = decode_token(token)
    if not payload:
        raise exc
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise exc
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise exc
    return user


class NotAuthenticatedException(Exception):
    pass


async def get_current_user_ui(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise NotAuthenticatedException("Token không tồn tại")

    payload = decode_token(token)
    if not payload:
        raise NotAuthenticatedException("Token không hợp lệ hoặc đã hết hạn")

    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise NotAuthenticatedException("Token không chứa user_id")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise NotAuthenticatedException("User không tồn tại hoặc bị khóa")

    return user


class NotAuthorizedException(Exception):
    pass


def require_ui_role(*roles: str):
    def checker(request: Request):
        user = getattr(request.state, "user", None)
        if not user or str(user.role) not in roles:
            raise NotAuthorizedException("Bạn không có quyền truy cập trang này.")
        return user
    return checker


def require_role(*roles: str):
    """
    Dependency factory kiểm tra role (dùng cho API routes).
    Admin luôn được phép truy cập.
    """
    role_set = set(roles)

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = str(current_user.role)
        # Admin bypass tất cả
        if user_role == "admin":
            return current_user
        if user_role not in role_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Không có quyền. Yêu cầu một trong các role: {list(role_set)}",
            )
        return current_user
    return checker


# ── PERMISSION CHECK TỪ DATABASE ──────────────────────────────────────────

async def has_permission(
    user: User,
    resource: str,
    action: str,   # "create" | "read" | "update" | "delete"
    db: AsyncSession,
) -> bool:
    """
    Kiểm tra user có quyền thực hiện action trên resource không,
    dựa trên bảng role_permissions trong DB.
    Admin luôn có toàn quyền.
    """
    if str(user.role) == "admin":
        return True

    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role == str(user.role),
            RolePermission.resource == resource,
        )
    )
    perm = result.scalar_one_or_none()
    if perm is None:
        return False

    col_map = {
        "create": perm.can_create,
        "read":   perm.can_read,
        "update": perm.can_update,
        "delete": perm.can_delete,
    }
    return bool(col_map.get(action, False))


def require_permission(resource: str, action: str):
    """
    Dependency factory — kiểm tra quyền từ DB.
    Admin luôn bypass.
    Dùng trong API routes thay thế require_role().

    Ví dụ:
        @router.post("", dependencies=[Depends(require_permission("candidates", "create"))])
    """
    async def checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        ok = await has_permission(current_user, resource, action, db)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bạn không có quyền '{action}' trên '{resource}'.",
            )
        return current_user
    return checker


def require_ui_permission(resource: str, action: str = "read"):
    """
    Dependency factory — kiểm tra quyền từ DB dành cho UI Routes.
    Nếu user không có quyền, sẽ raise NotAuthorizedException, 
    nhờ đó app/main.py redirect về trang báo lỗi.
    """
    async def checker(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> User:
        current_user = getattr(request.state, "user", None)
        if not current_user:
            raise NotAuthenticatedException("Token không tồn tại")
            
        ok = await has_permission(current_user, resource, action, db)
        if not ok:
            raise NotAuthorizedException(f"Bạn không có quyền '{action}' trên '{resource}'.")
        return current_user
    return checker
