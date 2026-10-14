from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import api_logger


class ApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int,
        errors: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.errors = errors


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "")) or "unknown"


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    errors: list[dict[str, str]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "code": code,
        "message": message,
        "data": None,
        "request_id": _request_id(request),
    }
    if errors:
        content["errors"] = errors
    response_headers = dict(headers or {})
    response_headers["X-Request-ID"] = _request_id(request)
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content),
        headers=response_headers,
    )


def _http_error_code(status_code: int) -> str:
    return {
        400: "BAD_REQUEST",
        401: "AUTH_REQUIRED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_FAILED",
        429: "RATE_LIMITED",
        503: "SERVICE_UNAVAILABLE",
    }.get(status_code, "HTTP_ERROR" if status_code < 500 else "INTERNAL_ERROR")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
        return _error_response(
            request,
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            errors=error.errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        status_code = error.status_code
        message = str(error.detail) if status_code < 500 else "服务暂时不可用，请稍后重试。"
        return _error_response(
            request,
            status_code=status_code,
            code=_http_error_code(status_code),
            message=message,
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(part) for part in item.get("loc", ()) if part != "body"),
                "code": str(item.get("type", "invalid")),
                "message": str(item.get("msg", "输入无效"))[:240],
            }
            for item in error.errors()
        ]
        return _error_response(
            request,
            status_code=422,
            code="VALIDATION_FAILED",
            message="请求参数校验失败。",
            errors=errors,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        request_id = _request_id(request)
        route = getattr(request.scope.get("route"), "path", request.url.path)
        api_logger.exception(
            "request_failed",
            extra={
                "event": "request_failed",
                "request_id": request_id,
                "method": request.method,
                "route": route,
                "status_code": 500,
                "error_code": "INTERNAL_ERROR",
            },
        )
        return _error_response(
            request,
            status_code=500,
            code="INTERNAL_ERROR",
            message="服务器内部错误，请稍后重试。",
        )


def success_envelope(data: Any, request_id: str) -> dict[str, Any]:
    return {
        "code": "OK",
        "message": "请求成功",
        "data": data,
        "request_id": request_id,
    }


def is_success_envelope(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and {"code", "message", "data", "request_id"}.issubset(value)
    )


