"""认证接口：登录、当前用户、修改密码、权限清单。"""
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..deps import get_current_user, user_permissions
from ..models import User
from ..utils import BusinessError, fail, ok
from ..utils.security import PasswordHasher, create_access_token

router = APIRouter(prefix="/api/auth", tags=["认证"])


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)


class ChangePwdBody(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=100)


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "phone": user.phone,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "roles": [{"id": r.id, "code": r.code, "name": r.name} for r in user.roles],
    }


@router.post("/login")
def login(body: LoginBody, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not PasswordHasher.verify(body.password, user.password_hash):
        write_audit(db, body.username, "login", "auth", target="登录失败", ip=request.client.host)
        db.commit()
        return fail("用户名或密码错误")
    if not user.is_active:
        return fail("账号已被禁用，请联系管理员")
    token = create_access_token(user.id, user.username)
    write_audit(db, user.username, "login", "auth", target="登录成功", ip=request.client.host)
    db.commit()
    return ok({"token": token, "user": _user_dict(user)}, "登录成功")


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return ok({"user": _user_dict(user), "permissions": user_permissions(user)})


@router.get("/permissions")
def permissions(user: User = Depends(get_current_user)):
    """当前用户拥有的权限点（前端据此渲染菜单/按钮）。"""
    return ok({"permissions": user_permissions(user)})


@router.post("/change-password")
def change_password(
    body: ChangePwdBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not PasswordHasher.verify(body.old_password, user.password_hash):
        return fail("原密码错误")
    user.password_hash = PasswordHasher.hash(body.new_password)
    write_audit(
        db, user.username, "update", "auth", target=f"修改密码(user#{user.id})", ip=request.client.host
    )
    db.commit()
    return ok(message="密码修改成功")