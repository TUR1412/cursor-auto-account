from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from flask import request

from .context import request_id_var, user_id_var

logger = logging.getLogger(__name__)


def register_request_context(app) -> None:
    @app.before_request
    def _before_request():
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_var.set(request_id)

        # Best-effort user id propagation (auth decorator sets request.current_user)
        try:
            current_user = getattr(request, "current_user", None)
            if current_user is not None and getattr(current_user, "id", None) is not None:
                user_id_var.set(str(current_user.id))
            else:
                user_id_var.set("-")
        except Exception:
            user_id_var.set("-")

        request._start_time = time.perf_counter()  # type: ignore[attr-defined]

    @app.after_request
    def _after_request(response):
        response.headers["X-Request-ID"] = request_id_var.get()

        duration_ms: Optional[float] = None
        try:
            start = getattr(request, "_start_time", None)
            if start is not None:
                duration_ms = (time.perf_counter() - start) * 1000.0
        except Exception:
            duration_ms = None

        if duration_ms is not None:
            logger.info(
                "%s %s -> %s (%.2fms)",
                request.method,
                request.path,
                response.status_code,
                duration_ms,
            )

        return response
