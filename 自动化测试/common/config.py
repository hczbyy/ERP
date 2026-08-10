"""全局配置：环境、账号、超时。

所有配置项均支持环境变量覆盖，便于多环境切换：
  ERP_BASE_URL  服务地址（默认 http://127.0.0.1:8000）
  ERP_USERNAME  登录账号（默认 admin）
  ERP_PASSWORD  登录密码（默认 admin123）
  ERP_TIMEOUT   请求超时秒数（默认 15）
"""
import os

BASE_URL = os.getenv("ERP_BASE_URL", "http://127.0.0.1:8000")
ADMIN_USERNAME = os.getenv("ERP_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ERP_PASSWORD", "admin123")
TIMEOUT = int(os.getenv("ERP_TIMEOUT", "15"))