"""安全工具：密码哈希（PBKDF2，标准库实现）、JWT 签发与校验。"""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from ..config import settings


class PasswordHasher:
    """PBKDF2-SHA256 密码哈希，格式: pbkdf2$iterations$salt_hex$hash_hex"""

    @staticmethod
    def hash(password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, settings.PASSWORD_SALT_ITERATIONS
        )
        return f"pbkdf2${settings.PASSWORD_SALT_ITERATIONS}${salt.hex()}${digest.hex()}"

    @staticmethod
    def verify(password: str, stored: str) -> bool:
        try:
            _, iterations, salt_hex, hash_hex = stored.split("$")
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
            )
            return hmac.compare_digest(digest.hex(), hash_hex)
        except (ValueError, AttributeError):
            return False


def create_access_token(user_id: int, username: str) -> str:
    """签发 JWT，携带用户标识。"""
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """校验 JWT，失败返回 None。"""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None