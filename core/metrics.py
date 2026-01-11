from __future__ import annotations

import logging
import time

from flask import Response, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)


def _endpoint_label() -> str:
    # Prefer the stable route rule; fallback to endpoint name; then raw path.
    try:
        if request.url_rule is not None and getattr(request.url_rule, "rule", None):
            return str(request.url_rule.rule)
    except Exception:
        pass

    try:
        if request.endpoint:
            return str(request.endpoint)
    except Exception:
        pass

    return request.path


def register_metrics(app) -> None:
    @app.before_request
    def _metrics_before_request():
        request._metrics_start_time = time.perf_counter()  # type: ignore[attr-defined]

    @app.after_request
    def _metrics_after_request(response):
        try:
            start = getattr(request, "_metrics_start_time", None)
            if start is not None:
                duration = time.perf_counter() - start
                endpoint = _endpoint_label()
                REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)
                REQUEST_COUNT.labels(request.method, endpoint, str(response.status_code)).inc()
        except Exception:
            logger.exception("Failed to record metrics")
        return response

    @app.get("/metrics")
    def metrics():  # noqa: A001
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

