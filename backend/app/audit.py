"""审计日志写入（同步写库，简单可靠）。"""
import json
from datetime import datetime

from sqlalchemy.orm import Session

from .models import AuditLog


def write_audit(
    db: Session,
    username: str,
    action: str,
    module: str,
    target: str | None = None,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    """记录一条审计日志。"""
    db.add(
        AuditLog(
            username=username,
            action=action,
            module=module,
            target=target,
            detail=json.dumps(detail, ensure_ascii=False, default=str) if detail else None,
            ip=ip,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
    )