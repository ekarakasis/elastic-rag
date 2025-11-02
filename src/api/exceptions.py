"""Custom exceptions and exception handlers for the API."""

import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.api.models import ErrorResponse

logger = logging.getLogger(__name__)


class FileValidationError(HTTPException):
    """Exception raised when file validation fails."""

    def __init__(self, detail: str):
        """Initialize file validation error.

        Args:
            detail: Error detail message
        """
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class FileTooLargeError(HTTPException):
    """Exception raised when uploaded file is too large."""

    def __init__(self, max_size_mb: int):
        """Initialize file too large error.

        Args:
            max_size_mb: Maximum allowed file size in MB
        """
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {max_size_mb}MB",
        )


class DocumentProcessingError(HTTPException):
    """Exception raised when document processing fails."""

    def __init__(self, detail: str):
        """Initialize document processing error.

        Args:
            detail: Error detail message
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


class QueryProcessingError(HTTPException):
    """Exception raised when query processing fails."""

    def __init__(self, detail: str):
        """Initialize query processing error.

        Args:
            detail: Error detail message
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


class CircuitBreakerOpenError(HTTPException):
    """Exception raised when circuit breaker is open."""

    def __init__(self):
        """Initialize circuit breaker open error."""
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service temporarily unavailable. Circuit breaker is open. Please retry later.",
            headers={"Retry-After": "60"},
        )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with structured error response.

    Args:
        request: The incoming request
        exc: The HTTP exception

    Returns:
        JSON response with error details
    """
    error_response = ErrorResponse(
        error=exc.__class__.__name__,
        message=str(exc.detail),
        detail=None,
        status_code=exc.status_code,
    )

    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail} - "
        f"Path: {request.url.path} - Method: {request.method}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
        headers=getattr(exc, "headers", None),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions with structured error response.

    Args:
        request: The incoming request
        exc: The uncaught exception

    Returns:
        JSON response with error details
    """
    error_response = ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred",
        detail=str(exc) if logger.level <= logging.DEBUG else None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    logger.error(
        f"Uncaught exception: {exc.__class__.__name__} - {exc} - "
        f"Path: {request.url.path} - Method: {request.method}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle validation exceptions from Pydantic.

    Args:
        request: The incoming request
        exc: The validation exception

    Returns:
        JSON response with validation error details
    """
    error_response = ErrorResponse(
        error="ValidationError",
        message="Request validation failed",
        detail=str(exc),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )

    logger.warning(f"Validation error: {exc} - Path: {request.url.path} - Method: {request.method}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )
