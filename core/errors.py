from __future__ import annotations

import logging
from typing import Any

from flask import jsonify
from werkzeug.exceptions import HTTPException

from .context import request_id_var

logger = logging.getLogger(__name__)


def _json_error(message: str, *, status_code: int, code: str | None = None, details: Any | None = None):
    payload: dict[str, Any] = {"status": "error", "message": message, "request_id": request_id_var.get()}
    if code:
        payload["code"] = code
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status_code


def register_error_handlers(app) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        # werkzeug uses "description" for message
        return _json_error(
            exc.description,
            status_code=exc.code or 500,
            code=getattr(exc, "name", "HTTP_ERROR"),
        )

    @app.errorhandler(Exception)
    def handle_unhandled_exception(exc: Exception):
        logger.exception("Unhandled exception")
        return _json_error("服务器内部错误", status_code=500, code="INTERNAL_SERVER_ERROR")

