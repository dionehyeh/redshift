import pytest

from app.config import _read_bool_env


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", True),
        ("true", True),
        (" YES ", True),
        ("on", True),
        ("0", False),
        ("false", False),
        (" No ", False),
        ("off", False),
    ],
)
def test_boolean_environment_values_are_parsed(monkeypatch, value, expected):
    monkeypatch.setenv("DEMO_MODE", value)

    assert _read_bool_env("DEMO_MODE") is expected


def test_boolean_environment_values_use_default_only_when_unset(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)

    assert _read_bool_env("DEMO_MODE") is False
    assert _read_bool_env("DEMO_MODE", default=True) is True


def test_invalid_boolean_environment_value_fails_clearly(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "sometimes")

    with pytest.raises(ValueError, match="DEMO_MODE must be a boolean value"):
        _read_bool_env("DEMO_MODE")
