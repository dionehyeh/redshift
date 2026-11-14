import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.status = status
        self.details = details if details is not None else {}


def _error_response(
    status: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=jsonable_encoder(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "details": details if details is not None else {},
                }
            }
        ),
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status, exc.code, exc.message, details=exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "location": list(error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return _error_response(
            422,
            "VALIDATION",
            "Invalid request parameters",
            details={"errors": errors},
        )

    @app.exception_handler(HTTPException)
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        known_errors = {
            401: ("UNAUTHENTICATED", "Authentication required"),
            403: ("FORBIDDEN", "Access forbidden"),
            404: ("NOT_FOUND", "Resource not found"),
            405: ("METHOD_NOT_ALLOWED", "Method not allowed"),
        }
        code, default_message = known_errors.get(
            exc.status_code, ("HTTP_ERROR", "Request failed")
        )
        message = exc.detail if isinstance(exc.detail, str) else default_message
        return _error_response(
            exc.status_code,
            code,
            message,
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def handle_generic_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled API exception for %s %s",
            request.method,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return _error_response(
            500,
            "INTERNAL",
            "An unexpected internal server error occurred",
        )
