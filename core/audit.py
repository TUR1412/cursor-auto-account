import json
import time
from typing import Any, Optional

from flask import request

from core.context import request_id_var
from models import AuditLog, User, db


def record_audit(
    *,
    action: str,
    user: Optional[User] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    detail: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """
    Persist an audit log entry.

    SECURITY:
    - Do NOT store credentials (password/token).
    - Keep detail small and non-sensitive.
    """

    detail_json = None
    if detail is not None:
        detail_json = json.dumps(detail, ensure_ascii=False)

    log = AuditLog(
        user_id=getattr(user, "id", None) if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=request_id_var.get(),
        ip=request.headers.get("X-Real-IP")
        or request.headers.get("X-Forwarded-For")
        or request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        detail=detail_json,
        created_at=int(time.time()),
    )
    db.session.add(log)
    return log
