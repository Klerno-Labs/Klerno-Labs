"""
Centralized exception handling for Klerno Labs.
Provides consistent error responses and logging.
"""

import traceback
from typing import Any

import structlog
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_config import log_security_event

logger = structlog.get_logger("exceptions")


class KlernoException(Exception):
    """Base exception for Klerno Labs application."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationException(KlernoException):
    """Exception for validation errors."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.field = field
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details or {},
        )


class AuthenticationException(KlernoException):
    """Exception for authentication errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details or {},
        )


class AuthorizationException(KlernoException):
    """Exception for authorization errors."""

    def __init__(
        self, message: str = "Access denied", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details or {},
        )


class ResourceNotFoundException(KlernoException):
    """Exception for resource not found errors."""

    def __init__(
        self,
        resource: str,
        identifier: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"

        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details=details or {},
        )


class RateLimitException(KlernoException):
    """Exception for rate limiting errors."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int | None = None
    ) -> None:
        details = {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
        )


class ExternalServiceException(KlernoException):
    """Exception for external service errors."""

    def __init__(
        self,
        service: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        msg = message or f"External service '{service}' unavailable"

        super().__init__(
            message=msg,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details=details or {"service": service},
        )


def create_error_response(
    error_code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    """Create standardized error response."""
    content = {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": logger._context.get("timestamp", ""),
        }
    }

    if details:
        content["error"]["details"] = details

    if request_id:
        content["error"]["request_id"] = request_id

    return JSONResponse(status_code=status_code, content=content)


async def klerno_exception_handler(
    request: Request, exc: KlernoException
) -> JSONResponse:
    """Handle Klerno application exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.error(
        "Application exception",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
    )

    return create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=request_id,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    request_id = getattr(request.state, "request_id", None)

    # Map status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
    }

    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")

    logger.warning(
        "HTTP exception",
        error_code=error_code,
        message=exc.detail,
        status_code=exc.status_code,
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
    )

    # Log security events for authentication / authorization failures
    if exc.status_code in [401, 403]:
        log_security_event(
            event_type=(
                "authentication_failure"
                if exc.status_code == 401
                else "authorization_failure"
            ),
            ip_address=request.client.host if request.client else None,
            details={"path": str(request.url.path), "method": request.method},
        )

    return create_error_response(
        error_code=error_code,
        message=exc.detail,
        status_code=exc.status_code,
        request_id=request_id,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation exceptions."""
    request_id = getattr(request.state, "request_id", None)

    # Extract validation errors
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning(
        "Validation error",
        error_code="VALIDATION_ERROR",
        errors=errors,
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
    )

    return create_error_response(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=422,
        details={"errors": errors},
        request_id=request_id,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.error(
        "Unexpected exception",
        error_code="INTERNAL_ERROR",
        exception_type=type(exc).__name__,
        message=str(exc),
        traceback=traceback.format_exc(),
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
    )

    return create_error_response(
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        status_code=500,
        request_id=request_id,
    )


def install_exception_handlers(app) -> None:
    """Install all exception handlers on the FastAPI app."""
    app.add_exception_handler(KlernoException, klerno_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
