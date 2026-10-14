import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, cast
from uuid import uuid4

from starlette.responses import JSONResponse

from app.core.api_responses import is_success_envelope, success_envelope
from app.core.logging import api_logger

ASGISend = Callable[[dict[str, Any]], Awaitable[None]]


class ApiResponseLoggingMiddleware:
    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: ASGISend) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = time.perf_counter()
        response_status = 500
        response_code: str | None = None
        response_start: dict[str, Any] | None = None
        response_body: list[bytes] = []
        should_buffer_json = False

        async def send_response(message: dict[str, Any]) -> None:
            nonlocal response_status, response_code, response_start, should_buffer_json
            message_type = message["type"]
            if message_type == "http.response.start":
                response_status = int(message["status"])
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() not in {b"x-request-id", b"content-length"}
                ]
                headers.append((b"x-request-id", request_id.encode("ascii")))
                content_type = next(
                    (
                        value.split(b";", 1)[0].strip().lower()
                        for key, value in headers
                        if key.lower() == b"content-type"
                    ),
                    b"",
                )
                is_attachment = any(
                    key.lower() == b"content-disposition"
                    and value.lower().startswith(b"attachment")
                    for key, value in headers
                )
                should_buffer_json = (
                    response_status not in {204, 304}
                    and not is_attachment
                    and (content_type == b"application/json" or content_type.endswith(b"+json"))
                )
                if should_buffer_json:
                    response_start = {**message, "headers": headers}
                    return
                await send({**message, "headers": headers})
                return

            if message_type == "http.response.body" and should_buffer_json:
                response_body.append(message.get("body", b""))
                if message.get("more_body", False):
                    return
                raw_body = b"".join(response_body)
                try:
                    value = json.loads(raw_body) if raw_body else None
                    if is_success_envelope(value):
                        cast(dict[str, Any], value)["request_id"] = request_id
                    else:
                        value = success_envelope(value, request_id)
                    body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode(
                        "utf-8"
                    )
                    response_code = str(value.get("code")) if isinstance(value, dict) else None
                except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
                    response_status = 500
                    response_code = "INTERNAL_ERROR"
                    body = json.dumps(
                        {
                            "code": "INTERNAL_ERROR",
                            "message": "服务器内部错误，请稍后重试。",
                            "data": None,
                            "request_id": request_id,
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode("utf-8")
                if response_start is not None:
                    headers = [
                        (key, value)
                        for key, value in response_start["headers"]
                        if key.lower() != b"content-length"
                    ]
                    headers.append((b"content-length", str(len(body)).encode("ascii")))
                    await send({**response_start, "headers": headers})
                await send({"type": "http.response.body", "body": body, "more_body": False})
                await self._log_request(
                    scope, request_id, response_status, response_code, started_at
                )
                return

            await send(message)
            if message_type == "http.response.body" and not message.get("more_body", False):
                await self._log_request(
                    scope, request_id, response_status, response_code, started_at
                )

        try:
            await self.app(scope, receive, send_response)
        except Exception:
            route = getattr(scope.get("route"), "path", scope.get("path", ""))
            api_logger.exception(
                "request_failed",
                extra={
                    "event": "request_failed",
                    "request_id": request_id,
                    "method": scope.get("method", ""),
                    "route": route,
                    "status_code": 500,
                    "error_code": "INTERNAL_ERROR",
                },
            )
            error_response = JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误，请稍后重试。",
                    "data": None,
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )
            await error_response(scope, receive, cast(Any, send_response))

    @staticmethod
    async def _log_request(
        scope: dict[str, Any],
        request_id: str,
        status_code: int,
        error_code: str | None,
        started_at: float,
    ) -> None:
        route = getattr(scope.get("route"), "path", scope.get("path", ""))
        api_logger.log(
            logging.ERROR
            if status_code >= 500
            else logging.WARNING
            if status_code >= 400
            else logging.INFO,
            "http_request",
            extra={
                "event": "http_request",
                "request_id": request_id,
                "method": scope.get("method", ""),
                "route": route,
                "status_code": status_code,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                "error_code": error_code if status_code >= 400 else None,
            },
        )
