from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.errors import AppError, register_error_handlers


def create_error_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/app-error")
    def app_error():
        raise AppError(
            "ACCOUNT_CONFLICT",
            "Account conflict",
            status=409,
            details={"contact": "already linked"},
        )

    @app.get("/http-error")
    def http_error():
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.get("/integer/{value}")
    def parse_integer(value: int):
        return {"value": value}

    @app.get("/unexpected-error")
    def unexpected_error():
        raise RuntimeError("private implementation detail")

    return app


def test_app_error_uses_standard_error_envelope():
    client = TestClient(create_error_app())

    response = client.get("/app-error")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "ACCOUNT_CONFLICT",
            "message": "Account conflict",
            "details": {"contact": "already linked"},
        }
    }


def test_http_exception_uses_standard_error_envelope_and_headers():
    client = TestClient(create_error_app())

    response = client.get("/http-error")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "error": {
            "code": "UNAUTHENTICATED",
            "message": "Authentication required",
            "details": {},
        }
    }


def test_validation_error_does_not_echo_submitted_value():
    client = TestClient(create_error_app())

    response = client.get("/integer/not-an-integer")

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION"
    assert body["error"]["details"]["errors"][0]["location"] == [
        "path",
        "value",
    ]
    assert "not-an-integer" not in response.text


def test_unexpected_error_is_generic_and_does_not_leak_exception():
    client = TestClient(create_error_app(), raise_server_exceptions=False)

    response = client.get("/unexpected-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL",
            "message": "An unexpected internal server error occurred",
            "details": {},
        }
    }
    assert "private implementation detail" not in response.text


def test_unknown_route_uses_standard_error_envelope():
    client = TestClient(create_error_app())

    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
