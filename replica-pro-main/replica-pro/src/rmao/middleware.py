"""FastAPI hardening: rate limits, JSON errors, and structured request logs."""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging.redaction import get_logger


logger = get_logger("rmao.http")
limiter = Limiter(key_func=get_remote_address, default_limits=[])


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log one JSON-safe request summary to stdout after every response."""

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
            )
            raise
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.monotonic() - started) * 1000, 2),
        )
        return response


def _error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


async def rate_limit_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Return a stable JSON response instead of slowapi's plain text body."""
    return JSONResponse(
        status_code=429,
        content=_error_payload("rate_limit_exceeded", "Too many requests"),
        headers={"Retry-After": "60"},
    )


async def validation_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_error_payload("validation_error", "Request validation failed", exc.errors()),
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=_error_payload("invalid_request", str(exc)),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Normalize framework and route-level HTTP errors."""
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            f"http_{exc.status_code}",
            detail,
            exc.detail if not isinstance(exc.detail, str) else None,
        ),
        headers=exc.headers,
    )


async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Hide internal details from clients while preserving a useful server log."""
    logger.exception(
        "unhandled_request_exception",
        method=request.method,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content=_error_payload("internal_server_error", "An internal server error occurred"),
    )


def install_middleware(app: FastAPI) -> FastAPI:
    """Install rate limiting, JSON exception handlers, and request logging."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, exception_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    return app


__all__ = [
    "install_middleware",
    "limiter",
    "exception_handler",
    "rate_limit_handler",
]