import json
import logging

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, Response
from httpx import ASGITransport, AsyncClient

from app.core.api_responses import ApiError, register_exception_handlers
from app.core.logging import JsonLogFormatter
from app.core.middleware import ApiResponseLoggingMiddleware


def create_test_app() -> FastAPI:
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.add_middleware(ApiResponseLoggingMiddleware)

    @test_app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"value": "ready"}

    @test_app.get("/created")
    async def created() -> JSONResponse:
        return JSONResponse({"id": "project-1"}, status_code=201)

    @test_app.get("/no-content")
    async def no_content() -> Response:
        return Response(status_code=204)

    @test_app.get("/redirect")
    async def redirect() -> RedirectResponse:
        return RedirectResponse("https://example.com/login", status_code=302)

    @test_app.get("/download")
    async def download() -> Response:
        return Response(
            '{"export":true}',
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="export.json"'},
        )

    @test_app.get("/http/{status_code}")
    async def http_error(status_code: int) -> None:
        raise HTTPException(status_code, "请求失败")

    @test_app.get("/csrf")
    async def csrf_error() -> None:
        raise ApiError("CSRF_INVALID", "请求校验失败", status_code=403)

    @test_app.get("/validate/{item_id}")
    async def validate(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    @test_app.get("/explode")
    async def explode() -> None:
        raise RuntimeError("internal database secret")

    return test_app


@pytest.mark.asyncio
async def test_json_success_envelope_and_request_id() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()), base_url="http://test"
    ) as client:
        response = await client.get("/ok")

    assert response.status_code == 200
    assert response.json() == {
        "code": "OK",
        "message": "请求成功",
        "data": {"value": "ready"},
        "request_id": response.headers["x-request-id"],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "code"),
    [(401, "AUTH_REQUIRED"), (403, "FORBIDDEN"), (404, "NOT_FOUND"), (409, "CONFLICT")],
)
async def test_http_errors_use_error_envelope(status_code: int, code: str) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()), base_url="http://test"
    ) as client:
        response = await client.get(f"/http/{status_code}")

    assert response.status_code == status_code
    assert response.json()["code"] == code
    assert response.json()["data"] is None
    assert response.json()["request_id"] == response.headers["x-request-id"]


@pytest.mark.asyncio
async def test_csrf_and_validation_errors_have_stable_shapes() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()), base_url="http://test"
    ) as client:
        csrf_response = await client.get("/csrf")
        validation_response = await client.get("/validate/not-an-integer")

    assert csrf_response.status_code == 403
    assert csrf_response.json()["code"] == "CSRF_INVALID"
    assert validation_response.status_code == 422
    assert validation_response.json()["code"] == "VALIDATION_FAILED"
    assert validation_response.json()["data"] is None
    assert validation_response.json()["errors"]


@pytest.mark.asyncio
async def test_unexpected_errors_are_sanitized_and_logged() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app(), raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/explode")

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert "internal database secret" not in response.text
    assert response.json()["request_id"] == response.headers["x-request-id"]


@pytest.mark.asyncio
async def test_non_json_responses_are_not_wrapped() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()), base_url="http://test"
    ) as client:
        created = await client.get("/created")
        no_content = await client.get("/no-content")
        redirect = await client.get("/redirect", follow_redirects=False)
        download = await client.get("/download")

    assert created.status_code == 201
    assert created.json()["data"] == {"id": "project-1"}
    assert no_content.status_code == 204
    assert no_content.content == b""
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://example.com/login"
    assert download.status_code == 200
    assert download.json() == {"export": True}
    assert download.headers["content-disposition"].startswith("attachment")


def test_json_log_formatter_redacts_credentials_and_omits_request_body() -> None:
    record = logging.LogRecord(
        "manxu.api",
        logging.INFO,
        __file__,
        1,
        "Authorization: Bearer bearer-secret api_key=api-secret",
        (),
        None,
    )
    record.request_id = "request-1"
    line = JsonLogFormatter().format(record)
    output = json.loads(line)

    assert "bearer-secret" not in line
    assert "api-secret" not in line
    assert "body" not in output
