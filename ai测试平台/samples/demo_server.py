# -*- coding: utf-8 -*-
"""示例商城后端服务：用于演示平台导入、AI 生成、执行、报告的完整流程。
运行：python samples/demo_server.py （监听 127.0.0.1:8080）"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPS_DIR = os.path.join(os.path.dirname(BASE_DIR), "ai测试平台依赖包")
if os.path.isdir(DEPS_DIR):
    sys.path.insert(0, DEPS_DIR)
sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, Header, HTTPException  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import uvicorn  # noqa: E402

app = FastAPI(title="示例商城服务")


class LoginBody(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6, max_length=32)


class CreateUserBody(BaseModel):
    name: str = Field(min_length=2, max_length=20)
    email: str
    role: str = "USER"


class UpdateUserBody(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=20)
    email: str | None = None
    role: str | None = None


class CreateOrderBody(BaseModel):
    goodsId: int = Field(ge=1)
    quantity: int = Field(ge=1, le=99)
    remark: str | None = Field(default=None, max_length=100)


USERS = [
    {"id": 1, "name": "张三", "email": "zhangsan@example.com", "role": "ADMIN"},
    {"id": 2, "name": "李四", "email": "lisi@example.com", "role": "USER"},
]
ORDERS = [
    {"id": 1001, "orderNo": "SO20260811001", "status": "PENDING", "amount": 99.9},
]
NEXT_USER_ID = 3
NEXT_ORDER_ID = 1002


def ok(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


def check_auth(authorization: str):
    if not authorization or not str(authorization).startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": 401, "message": "未登录或 token 失效"})
    return str(authorization)[len("Bearer "):]


@app.post("/api/v1/users/login")
def login(body: LoginBody):
    if body.username == "tester01" and body.password == "123456":
        return ok({"token": f"demo-token-{body.username}", "userId": 1})
    raise HTTPException(status_code=401, detail={"code": 1001, "message": "用户名或密码错误"})


@app.get("/api/v1/users")
def list_users(page: int = 1, size: int = 10, keyword: str = ""):
    items = USERS
    if keyword:
        items = [u for u in items if keyword in u["name"]]
    start = (page - 1) * size
    return ok({"list": items[start:start + size], "total": len(items)})


@app.post("/api/v1/users")
def create_user(body: CreateUserBody):
    global NEXT_USER_ID
    if "@" not in body.email:
        raise HTTPException(status_code=400, detail={"code": 1002, "message": "email 格式错误"})
    if body.role not in ("ADMIN", "USER"):
        raise HTTPException(status_code=400, detail={"code": 1003, "message": "role 不合法"})
    user = {"id": NEXT_USER_ID, "name": body.name, "email": body.email, "role": body.role}
    USERS.append(user)
    NEXT_USER_ID += 1
    return ok(user)


@app.get("/api/v1/users/{user_id}")
def user_detail(user_id: int):
    for u in USERS:
        if u["id"] == user_id:
            return ok(u)
    raise HTTPException(status_code=404, detail={"code": 1004, "message": "用户不存在"})


@app.put("/api/v1/users/{user_id}")
def update_user(user_id: int, body: UpdateUserBody, authorization: str = Header(default="")):
    check_auth(authorization)
    for u in USERS:
        if u["id"] == user_id:
            if body.name is not None:
                u["name"] = body.name
            if body.email is not None:
                u["email"] = body.email
            if body.role is not None:
                u["role"] = body.role
            return ok(u)
    raise HTTPException(status_code=404, detail={"code": 1004, "message": "用户不存在"})


@app.delete("/api/v1/users/{user_id}")
def delete_user(user_id: int, authorization: str = Header(default="")):
    check_auth(authorization)
    global USERS
    before = len(USERS)
    USERS = [u for u in USERS if u["id"] != user_id]
    if len(USERS) == before:
        raise HTTPException(status_code=404, detail={"code": 1004, "message": "用户不存在"})
    return ok()


@app.get("/api/v1/orders")
def list_orders(status: str = "", page: int = 1, authorization: str = Header(default="")):
    check_auth(authorization)
    items = [o for o in ORDERS if not status or o["status"] == status]
    return ok({"list": items, "total": len(items)})


@app.post("/api/v1/orders")
def create_order(body: CreateOrderBody, authorization: str = Header(default="")):
    check_auth(authorization)
    global NEXT_ORDER_ID
    order = {"id": NEXT_ORDER_ID, "orderNo": f"SO2026{NEXT_ORDER_ID:07d}", "status": "PENDING", "amount": 88.0}
    ORDERS.append(order)
    NEXT_ORDER_ID += 1
    return ok(order)


if __name__ == "__main__":
    print("=" * 56)
    print("  示例商城服务已启动: http://127.0.0.1:8080")
    print("  登录账号: tester01 / 123456")
    print("  关闭本窗口即可停止")
    print("=" * 56)
    uvicorn.run(app, host="127.0.0.1", port=8080)
