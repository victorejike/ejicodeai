from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "ejicode_http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "ejicode_http_request_latency_seconds",
    "HTTP request latency",
    ["method", "path"],
)
EXCEPTIONS_COUNT = Counter(
    "ejicode_http_exceptions_total",
    "Total number of HTTP exceptions",
    ["method", "path", "exception"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to record Prometheus metrics for HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path
        with REQUEST_LATENCY.labels(method=method, path=path).time():
            try:
                response = await call_next(request)
            except Exception as exc:
                EXCEPTIONS_COUNT.labels(method=method, path=path, exception=type(exc).__name__).inc()
                raise

        REQUEST_COUNT.labels(method=method, path=path, status=str(response.status_code)).inc()
        return response


def metrics_endpoint() -> Response:
    """Return Prometheus metrics."""
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
