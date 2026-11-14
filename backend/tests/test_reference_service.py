import json
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import AppError, register_error_handlers
from app.routers import reference
from app.services import reference_service


def write_outlook_data(tmp_path, forecasts):
    (tmp_path / "outlooks.json").write_text(
        json.dumps({"forecasts": forecasts}),
        encoding="utf-8",
    )


def create_reference_client():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(reference.router, prefix="/api/v1")
    return TestClient(app)


def test_explainers_report_the_language_the_content_is_actually_in():
    english = reference_service.get_explainers("en")
    malayalam = reference_service.get_explainers("ml")
    english_by_key = {card["key"]: card for card in english}
    malayalam_by_key = {card["key"]: card for card in malayalam}

    translated = {
        "rainfall_anomaly",
        "ndvi",
        "water_balance",
        "normals",
        "confidence",
        "estimates_not_guarantees",
    }
    assert set(english_by_key) == set(malayalam_by_key)
    assert all(card["lang"] == "en" for card in english)
    assert {key for key, card in malayalam_by_key.items() if card["lang"] == "ml"} == translated
    for key in translated:
        assert malayalam_by_key[key]["title"] != english_by_key[key]["title"]
        assert malayalam_by_key[key]["body"] != english_by_key[key]["body"]
    for key in set(malayalam_by_key) - translated:
        assert malayalam_by_key[key] == english_by_key[key]


def test_explainer_api_rejects_unsupported_language_and_reports_fallback():
    client = create_reference_client()

    unsupported = client.get("/api/v1/explainers?lang=fr")
    localized = client.get("/api/v1/explainers/rainfall_anomaly?lang=ml")
    fallback = client.get("/api/v1/explainers/rotation?lang=ml")

    assert unsupported.status_code == 422
    assert localized.status_code == 200
    assert localized.json()["lang"] == "ml"
    assert fallback.status_code == 200
    assert fallback.json()["lang"] == "en"
    assert "rotation" == fallback.json()["key"]


def test_outlook_returns_only_a_current_verified_reference(monkeypatch, tmp_path):
    forecasts = [
        {
            "region": "kerala",
            "label": "near normal",
            "factor_range": [0.95, 1.05],
            "source": "IMD Seasonal Monsoon Outlook, issued 2026-05-20",
            "valid_from": "2026-06-01",
            "valid_through": "2026-09-30",
            "valid_for": "2026 Southwest Monsoon",
            "entered_on": "2026-05-21",
        }
    ]
    write_outlook_data(tmp_path, forecasts)
    monkeypatch.setattr(reference_service, "DATA_DIR", tmp_path)

    result = reference_service.get_seasonal_outlook(
        "Kerala", today=date(2026, 7, 1)
    )

    assert result == {
        "region": "Kerala",
        "label": "near normal",
        "factor_range": [0.95, 1.05],
        "source": "IMD Seasonal Monsoon Outlook, issued 2026-05-20",
        "valid_for": "2026 Southwest Monsoon",
        "entered_on": "2026-05-21",
    }


def test_outlook_prefers_the_latest_current_bulletin(monkeypatch, tmp_path):
    first = {
        "region": "kerala",
        "label": "below normal",
        "factor_range": [0.8, 0.95],
        "source": "Older IMD bulletin",
        "valid_from": "2026-06-01",
        "valid_through": "2026-09-30",
        "valid_for": "2026 Southwest Monsoon",
        "entered_on": "2026-05-21",
    }
    latest = {
        **first,
        "label": "near normal",
        "factor_range": [0.95, 1.05],
        "source": "Revised IMD bulletin",
        "entered_on": "2026-06-10",
    }
    write_outlook_data(tmp_path, [first, latest])
    monkeypatch.setattr(reference_service, "DATA_DIR", tmp_path)

    result = reference_service.get_seasonal_outlook(
        "kerala", today=date(2026, 7, 1)
    )

    assert result["label"] == "near normal"
    assert result["source"] == "Revised IMD bulletin"


@pytest.mark.parametrize(
    ("region", "today"),
    [
        ("kerala", date(2026, 10, 1)),
        ("tamil nadu", date(2026, 7, 1)),
    ],
)
def test_outlook_is_unavailable_when_expired_or_missing_for_region(
    monkeypatch, tmp_path, region, today
):
    write_outlook_data(
        tmp_path,
        [
            {
                "region": "kerala",
                "label": "near normal",
                "factor_range": [0.95, 1.05],
                "source": "IMD bulletin",
                "valid_from": "2026-06-01",
                "valid_through": "2026-09-30",
                "valid_for": "2026 Southwest Monsoon",
                "entered_on": "2026-05-21",
            }
        ],
    )
    monkeypatch.setattr(reference_service, "DATA_DIR", tmp_path)

    with pytest.raises(AppError) as error:
        reference_service.get_seasonal_outlook(region, today=today)

    assert error.value.code == "OUTLOOK_UNAVAILABLE"
    assert error.value.status == 503


def test_outlook_rejects_invalid_factor_ranges(monkeypatch, tmp_path):
    write_outlook_data(
        tmp_path,
        [
            {
                "region": "kerala",
                "label": "near normal",
                "factor_range": [1.1, 0.9],
                "source": "IMD bulletin",
                "valid_from": "2026-06-01",
                "valid_through": "2026-09-30",
                "valid_for": "2026 Southwest Monsoon",
                "entered_on": "2026-05-21",
            }
        ],
    )
    monkeypatch.setattr(reference_service, "DATA_DIR", tmp_path)

    with pytest.raises(AppError) as error:
        reference_service.get_seasonal_outlook(
            "kerala", today=date(2026, 7, 1)
        )

    assert error.value.code == "OUTLOOK_DATA_INVALID"


def test_public_outlook_api_does_not_invent_a_missing_forecast(
    monkeypatch, tmp_path
):
    write_outlook_data(tmp_path, [])
    monkeypatch.setattr(reference_service, "DATA_DIR", tmp_path)
    client = create_reference_client()

    response = client.get("/api/v1/outlook")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "OUTLOOK_UNAVAILABLE"
