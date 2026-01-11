import os
import threading
import time
from functools import wraps

from flask import jsonify, request

_LOCK = threading.Lock()
_BUCKETS = {}


def _enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"


def _client_ip() -> str:
    return (
        request.headers.get("X-Real-IP")
        or request.headers.get("X-Forwarded-For")
        or request.remote_addr
        or "-"
    )


def rate_limit(*, limit: int, window_seconds: int, key_prefix: str = "rl"):
    """
    Simple in-memory fixed-window rate limiter.

    This is a lightweight guardrail, not a distributed/production-grade limiter.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not _enabled():
                return func(*args, **kwargs)

            key = f"{key_prefix}:{_client_ip()}"
            now = int(time.time())

            with _LOCK:
                count, reset_at = _BUCKETS.get(key, (0, now + window_seconds))
                if now >= reset_at:
                    count, reset_at = 0, now + window_seconds

                count += 1
                _BUCKETS[key] = (count, reset_at)

                if count > limit:
                    retry_after = max(1, reset_at - now)

                # Best-effort cleanup to avoid unbounded growth.
                max_buckets = int(os.getenv("RATE_LIMIT_MAX_BUCKETS", "5000"))
                if len(_BUCKETS) > max_buckets:
                    expired_keys = [k for k, (_, ra) in _BUCKETS.items() if now >= ra]
                    for k in expired_keys:
                        _BUCKETS.pop(k, None)

            if count > limit:
                resp = jsonify({"status": "error", "message": "请求过于频繁，请稍后再试"})
                resp.status_code = 429
                resp.headers["Retry-After"] = str(retry_after)
                return resp

            return func(*args, **kwargs)

        return wrapper

    return decorator
