"""工具函数：JWT Token、密码哈希、分页辅助、缓存装饰器

设计要点：
  - JWT 无状态 Token → 跨 Gunicorn 多进程工作
  - 缓存装饰器 → 消除热点 DB 查询，按 TTL 自动过期
"""

import hashlib
from datetime import datetime, timezone

from itsdangerous import URLSafeTimedSerializer
from flask import current_app

# ── JWT Token（无状态，跨进程） ──────────────────────────

def _get_serializer():
    """惰性获取 serializer，避免导入时 app 未初始化"""
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt=current_app.config["JWT_SALT"],
    )


def generate_token(user_id: int) -> str:
    """签发无状态 JWT Token"""
    s = _get_serializer()
    return s.dumps({"user_id": user_id})


def verify_token(token: str) -> int | None:
    """验证 Token，返回 user_id 或 None"""
    s = _get_serializer()
    max_age = current_app.config["JWT_EXPIRE_HOURS"] * 3600
    try:
        data = s.loads(token, max_age=max_age)
        return data["user_id"]
    except Exception:
        return None


# ── 密码处理 ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    """SHA-256（轻量，压测友好）"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


# ── 分页辅助 ──────────────────────────────────────────────

def paginate(query, page: int, per_page: int = 20):
    """分页，返回 {items, total, page, per_page, pages}"""
    total = query.count()
    pages = (total + per_page - 1) // per_page
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


# ── 内存缓存装饰器 ───────────────────────────────────────
# 使用 cachetools.TTLCache 实现，按 TTL 自动过期
# 每个 worker 独立缓存（Gunicorn 多进程下天然隔离，无锁竞争）

from cachetools import TTLCache
from functools import wraps


def cached(ttl: int, maxsize: int = 100):
    """方法级缓存装饰器，按 (args, kwargs) 缓存结果

    用法:
        @cached(ttl=10)
        def get_data(param):
            ...
    """
    # 每个装饰器实例拥有独立 cache 实例
    cache = TTLCache(maxsize=maxsize, ttl=ttl)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 不能用 kwargs 做 key（dict 不可哈希），用 frozenset
            key = (args, frozenset(kwargs.items()))
            if key in cache:
                return cache[key]
            result = fn(*args, **kwargs)
            cache[key] = result
            return result
        return wrapper
    return decorator


def make_cache_key(*args, **kwargs) -> str:
    """生成统一的缓存 key 字符串"""
    parts = [str(a) for a in args]
    parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(parts)