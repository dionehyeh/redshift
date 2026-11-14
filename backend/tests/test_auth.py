from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import deps
from app.errors import register_error_handlers
from app.routers import auth


class FakeCursor:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, profile):
        self.profile = dict(profile)
        self.inserted_user = None
        self.existing_user_id = None

    def execute(self, query, params=None):
        if query.startswith("UPDATE users SET language"):
            self.profile["language"] = params[0]
            return FakeCursor()
        if query.startswith("UPDATE farmer_prefs SET market_toggle"):
            self.profile["market_toggle"] = params[0]
            return FakeCursor()
        if query.startswith("UPDATE farmer_prefs SET default_share_consent"):
            self.profile["default_share_consent"] = params[0]
            return FakeCursor()
        if query.startswith("INSERT INTO users"):
            self.inserted_user = params
            return FakeCursor({"id": 7})
        if query.startswith("SELECT id FROM users WHERE clerk_user_id"):
            row = {"id": self.existing_user_id} if self.existing_user_id else None
            return FakeCursor(row)
        if query.startswith("SELECT u.id"):
            return FakeCursor(dict(self.profile))
        return FakeCursor()


def create_profile_client(monkeypatch, profile):
    connection = FakeConnection(profile)

    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(auth, "get_db", fake_get_db)
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(auth.user_router, prefix="/api/v1")
    app.dependency_overrides[deps.current_user] = lambda: dict(profile)
    return TestClient(app), connection


def test_profile_requires_clerk_session():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(auth.user_router, prefix="/api/v1")

    response = TestClient(app).get("/api/v1/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_valid_clerk_session_loads_existing_local_profile(monkeypatch):
    profile = {
        "id": 4,
        "name": "A Farmer",
        "role": "farmer",
        "language": "en",
        "contact": "farmer@example.test",
        "helper_type": None,
        "market_toggle": None,
        "default_share_consent": 0,
    }
    connection = FakeConnection(profile)
    connection.existing_user_id = 4

    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(deps, "decode_clerk_token", lambda token: {"sub": "user_123"})
    monkeypatch.setattr(deps, "get_db", fake_get_db)

    user = deps.current_user("Bearer clerk-session-token")

    assert user == profile


def test_get_profile_includes_application_preferences(monkeypatch):
    profile = {
        "id": 4,
        "name": "A Farmer",
        "role": "farmer",
        "language": "ml",
        "contact": "farmer@example.test",
        "helper_type": None,
        "market_toggle": "play_safe",
        "default_share_consent": 1,
    }
    client, _ = create_profile_client(monkeypatch, profile)

    response = client.get("/api/v1/me")

    assert response.status_code == 200
    assert response.json() == profile


def test_update_preferences_returns_updated_profile(monkeypatch):
    profile = {
        "id": 4,
        "name": "A Farmer",
        "role": "farmer",
        "language": "en",
        "contact": "farmer@example.test",
        "helper_type": None,
        "market_toggle": None,
        "default_share_consent": 0,
    }
    client, connection = create_profile_client(monkeypatch, profile)

    response = client.patch(
        "/api/v1/me/prefs",
        json={
            "language": "ml",
            "market_toggle": "earn_more",
            "default_share_consent": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["language"] == "ml"
    assert response.json()["market_toggle"] == "earn_more"
    assert response.json()["default_share_consent"] == 1
    assert connection.profile["language"] == "ml"


def test_preferences_reject_out_of_range_consent_value(monkeypatch):
    profile = {
        "id": 4,
        "name": "A Farmer",
        "role": "farmer",
        "language": "en",
        "contact": "farmer@example.test",
        "helper_type": None,
        "market_toggle": None,
        "default_share_consent": 0,
    }
    client, _ = create_profile_client(monkeypatch, profile)

    response = client.patch("/api/v1/me/prefs", json={"default_share_consent": 2})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"


def test_market_preference_can_be_cleared(monkeypatch):
    profile = {
        "id": 4,
        "name": "A Farmer",
        "role": "farmer",
        "language": "en",
        "contact": "farmer@example.test",
        "helper_type": None,
        "market_toggle": "play_safe",
        "default_share_consent": 0,
    }
    client, connection = create_profile_client(monkeypatch, profile)

    response = client.patch("/api/v1/me/prefs", json={"market_toggle": None})

    assert response.status_code == 200
    assert response.json()["market_toggle"] is None
    assert connection.profile["market_toggle"] is None


def test_clerk_provisioning_uses_only_trusted_public_role(monkeypatch):
    profile = {
        "id": "user_123",
        "first_name": "A",
        "last_name": "Farmer",
        "email_addresses": [{"id": "email_1", "email_address": "farmer@example.test"}],
        "primary_email_address_id": "email_1",
        "public_metadata": {},
        "unsafe_metadata": {"role": "admin"},
    }
    connection = FakeConnection(
        {
            "id": 7,
            "name": "A Farmer",
            "role": "farmer",
            "language": "en",
            "contact": "farmer@example.test",
            "helper_type": None,
            "market_toggle": None,
            "default_share_consent": 0,
        }
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return profile

    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(deps.settings, "clerk_secret_key", "test-secret")
    monkeypatch.setattr(deps.httpx, "get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(deps, "get_db", fake_get_db)

    user = deps._sync_clerk_user("user_123")

    assert connection.inserted_user[0:3] == ("user_123", "farmer", None)
    assert user["role"] == "farmer"
    assert user["contact"] == "farmer@example.test"
