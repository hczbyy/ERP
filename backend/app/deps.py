"""FastAPI 依赖：当前用户、权限校验。"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import Permission, Role, User
from .utils.security import decode_access_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """从 Authorization: Bearer <token> 解析当前用户。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    payload = decode_access_token(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录凭证无效或已过期")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    return user


def require_permission(permission_code: str):
    """权限依赖工厂：超级管理员直接放行，否则校验角色权限点。"""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.is_superuser:
            return user
        codes = {
            p.code
            for role in user.roles
            for p in role.permissions
        }
        if permission_code not in codes:
            raise HTTPException(status_code=403, detail=f"无权限：需要「{permission_code}」权限")
        return user

    return checker


def user_permissions(user: User) -> list[str]:
    """当前用户拥有的全部权限点编码。"""
    if user.is_superuser:
        return ["*"]
    return sorted({p.code for role in user.roles for p in role.permissions})