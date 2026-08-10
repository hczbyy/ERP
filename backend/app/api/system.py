"""系统管理接口：用户、角色、权限、部门、员工、审计日志。"""
from datetime import date

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..deps import get_current_user, require_permission
from ..models import (
    AuditLog, Department, Employee, Permission, Role, User,
)
from ..utils import BusinessError, fail, ok
from ..utils.pagination import paginate
from ..utils.security import PasswordHasher

router = APIRouter(prefix="/api/system", tags=["系统管理"])

# ---------- 用户 ----------


class UserBody(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    display_name: str = Field(min_length=1, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=100)
    email: str | None = None
    phone: str | None = None
    role_ids: list[int] = []


def _user_row(u: User) -> dict:
    return {
        "id": u.id, "username": u.username, "display_name": u.display_name,
        "email": u.email, "phone": u.phone, "is_active": u.is_active,
        "is_superuser": u.is_superuser,
        "roles": [{"id": r.id, "code": r.code, "name": r.name} for r in u.roles],
        "created_at": str(u.created_at),
    }


@router.get("/users")
def list_users(
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("system:user:manage")),
):
    q = db.query(User)
    if keyword:
        q = q.filter(or_(User.username.like(f"%{keyword}%"), User.display_name.like(f"%{keyword}%")))
    result = paginate(db, q.order_by(User.id), page, page_size)
    result["items"] = [_user_row(u) for u in result["items"]]
    return ok(result)


@router.post("/users")
def create_user(
    body: UserBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("system:user:manage")),
):
    if db.query(User).filter(User.username == body.username).first():
        return fail(f"用户名 {body.username} 已存在")
    u = User(
        username=body.username,
        display_name=body.display_name,
        password_hash=PasswordHasher.hash(body.password or "123456"),
        email=body.email, phone=body.phone,
    )
    if body.role_ids:
        u.roles = db.query(Role).filter(Role.id.in_(body.role_ids)).all()
    db.add(u)
    db.flush()
    write_audit(db, user.username, "create", "system", target=f"用户 {body.username}", ip=request.client.host)
    db.commit()
    return ok(_user_row(u), "用户创建成功")


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    body: UserBody,
    request: Request,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:user:manage")),
):
    u = db.get(User, user_id)
    if not u:
        return fail("用户不存在")
    if u.username != body.username and db.query(User).filter(User.username == body.username).first():
        return fail(f"用户名 {body.username} 已存在")
    u.username = body.username
    u.display_name = body.display_name
    u.email = body.email
    u.phone = body.phone
    if body.password:
        u.password_hash = PasswordHasher.hash(body.password)
    if body.role_ids is not None:
        u.roles = db.query(Role).filter(Role.id.in_(body.role_ids)).all()
    write_audit(db, op.username, "update", "system", target=f"用户 {u.username}", ip=request.client.host)
    db.commit()
    return ok(_user_row(u), "用户更新成功")


@router.post("/users/{user_id}/toggle-active")
def toggle_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:user:manage")),
):
    u = db.get(User, user_id)
    if not u:
        return fail("用户不存在")
    if u.id == op.id:
        return fail("不能禁用自己")
    if u.is_superuser:
        return fail("不能禁用超级管理员")
    u.is_active = not u.is_active
    write_audit(db, op.username, "update", "system", target=f"{'禁用' if not u.is_active else '启用'}用户 {u.username}", ip=request.client.host)
    db.commit()
    return ok(_user_row(u), "操作成功")


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:user:manage")),
):
    u = db.get(User, user_id)
    if not u:
        return fail("用户不存在")
    if u.id == op.id:
        return fail("不能删除自己")
    if u.is_superuser:
        return fail("不能删除超级管理员")
    db.delete(u)
    write_audit(db, op.username, "delete", "system", target=f"用户 {u.username}", ip=request.client.host)
    db.commit()
    return ok(message="用户已删除")


# ---------- 角色与权限 ----------


class RoleBody(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=50)
    description: str | None = None
    permission_ids: list[int] = []


@router.get("/roles")
def list_roles(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("system:role:manage")),
):
    roles = db.query(Role).all()
    return ok(
        [
            {
                "id": r.id, "code": r.code, "name": r.name,
                "description": r.description, "is_builtin": r.is_builtin,
                "permission_ids": [p.id for p in r.permissions],
            }
            for r in roles
        ]
    )


@router.get("/permissions")
def list_permissions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """全部权限点（分组返回，前端配置角色用）。"""
    perms = db.query(Permission).all()
    groups: dict[str, list] = {}
    for p in perms:
        groups.setdefault(p.module, []).append({"id": p.id, "code": p.code, "name": p.name})
    return ok({"groups": groups})


@router.post("/roles")
def create_role(
    body: RoleBody,
    request: Request,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:role:manage")),
):
    if db.query(Role).filter(Role.code == body.code).first():
        return fail(f"角色编码 {body.code} 已存在")
    role = Role(code=body.code, name=body.name, description=body.description)
    if body.permission_ids:
        role.permissions = db.query(Permission).filter(Permission.id.in_(body.permission_ids)).all()
    db.add(role)
    db.flush()
    write_audit(db, op.username, "create", "system", target=f"角色 {body.name}", ip=request.client.host)
    db.commit()
    return ok({"id": role.id}, "角色创建成功")


@router.put("/roles/{role_id}")
def update_role(
    role_id: int,
    body: RoleBody,
    request: Request,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:role:manage")),
):
    role = db.get(Role, role_id)
    if not role:
        return fail("角色不存在")
    role.code, role.name, role.description = body.code, body.name, body.description
    role.permissions = db.query(Permission).filter(Permission.id.in_(body.permission_ids)).all()
    write_audit(db, op.username, "update", "system", target=f"角色 {body.name}", ip=request.client.host)
    db.commit()
    return ok(message="角色更新成功")


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:role:manage")),
):
    role = db.get(Role, role_id)
    if not role:
        return fail("角色不存在")
    if role.is_builtin:
        return fail("内置角色不可删除")
    if role.users:
        return fail("该角色已分配给用户，无法删除")
    db.delete(role)
    write_audit(db, op.username, "delete", "system", target=f"角色 {role.name}", ip=request.client.host)
    db.commit()
    return ok(message="角色已删除")


# ---------- 部门 ----------


class DeptBody(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=50)
    leader: str | None = None
    phone: str | None = None
    remark: str | None = None


@router.get("/departments")
def list_departments(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("system:org:manage")),
):
    depts = db.query(Department).order_by(Department.id).all()
    return ok(
        [{"id": d.id, "code": d.code, "name": d.name, "leader": d.leader,
          "phone": d.phone, "remark": d.remark} for d in depts]
    )


@router.post("/departments")
def create_department(
    body: DeptBody,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:org:manage")),
):
    if db.query(Department).filter(Department.code == body.code).first():
        return fail(f"部门编码 {body.code} 已存在")
    d = Department(**body.model_dump())
    db.add(d)
    db.flush()
    write_audit(db, op.username, "create", "system", target=f"部门 {body.name}")
    db.commit()
    return ok({"id": d.id}, "部门创建成功")


@router.put("/departments/{dept_id}")
def update_department(
    dept_id: int, body: DeptBody,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:org:manage")),
):
    d = db.get(Department, dept_id)
    if not d:
        return fail("部门不存在")
    for k, v in body.model_dump().items():
        setattr(d, k, v)
    write_audit(db, op.username, "update", "system", target=f"部门 {body.name}")
    db.commit()
    return ok(message="部门更新成功")


@router.delete("/departments/{dept_id}")
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:org:manage")),
):
    d = db.get(Department, dept_id)
    if not d:
        return fail("部门不存在")
    if db.query(Employee).filter(Employee.department_id == dept_id).first():
        return fail("该部门下存在员工，无法删除")
    db.delete(d)
    write_audit(db, op.username, "delete", "system", target=f"部门 {d.name}")
    db.commit()
    return ok(message="部门已删除")


# ---------- 员工 ----------


class EmployeeBody(BaseModel):
    emp_no: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=50)
    gender: str | None = None
    phone: str | None = None
    email: str | None = None
    hire_date: str | None = None
    position: str | None = None
    status: str = "active"
    department_id: int | None = None


def _emp_row(e: Employee) -> dict:
    return {
        "id": e.id, "emp_no": e.emp_no, "name": e.name, "gender": e.gender,
        "phone": e.phone, "email": e.email, "hire_date": str(e.hire_date) if e.hire_date else None,
        "position": e.position, "status": e.status,
        "department_id": e.department_id,
        "department_name": e.department.name if e.department else None,
    }


@router.get("/employees")
def list_employees(
    keyword: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("system:org:manage")),
):
    q = db.query(Employee)
    if keyword:
        q = q.filter(or_(Employee.name.like(f"%{keyword}%"), Employee.emp_no.like(f"%{keyword}%")))
    result = paginate(db, q.order_by(Employee.id), page, page_size)
    result["items"] = [_emp_row(e) for e in result["items"]]
    return ok(result)


@router.post("/employees")
def create_employee(
    body: EmployeeBody,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:org:manage")),
):
    if db.query(Employee).filter(Employee.emp_no == body.emp_no).first():
        return fail(f"工号 {body.emp_no} 已存在")
    data = body.model_dump()
    if data.get("hire_date"):
        data["hire_date"] = date.fromisoformat(data["hire_date"])
    e = Employee(**data)
    db.add(e)
    db.flush()
    write_audit(db, op.username, "create", "system", target=f"员工 {body.name}")
    db.commit()
    return ok({"id": e.id}, "员工创建成功")


@router.put("/employees/{emp_id}")
def update_employee(
    emp_id: int, body: EmployeeBody,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:org:manage")),
):
    e = db.get(Employee, emp_id)
    if not e:
        return fail("员工不存在")
    data = body.model_dump()
    if data.get("hire_date"):
        data["hire_date"] = date.fromisoformat(data["hire_date"])
    for k, v in data.items():
        setattr(e, k, v)
    write_audit(db, op.username, "update", "system", target=f"员工 {body.name}")
    db.commit()
    return ok(message="员工更新成功")


@router.delete("/employees/{emp_id}")
def delete_employee(
    emp_id: int,
    db: Session = Depends(get_db),
    op: User = Depends(require_permission("system:org:manage")),
):
    e = db.get(Employee, emp_id)
    if not e:
        return fail("员工不存在")
    db.delete(e)
    write_audit(db, op.username, "delete", "system", target=f"员工 {e.name}")
    db.commit()
    return ok(message="员工已删除")


# ---------- 审计日志 ----------


@router.get("/audit-logs")
def list_audit_logs(
    keyword: str = "", action: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("system:audit:read")),
):
    q = db.query(AuditLog)
    if keyword:
        q = q.filter(AuditLog.target.like(f"%{keyword}%"))
    if action:
        q = q.filter(AuditLog.action == action)
    result = paginate(db, q.order_by(AuditLog.id.desc()), page, page_size)
    result["items"] = [
        {
            "id": a.id, "username": a.username, "action": a.action,
            "module": a.module, "target": a.target, "detail": a.detail,
            "ip": a.ip, "created_at": a.created_at,
        }
        for a in result["items"]
    ]
    return ok(result)