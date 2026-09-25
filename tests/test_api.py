from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_recommendation_endpoint_returns_ranked_results() -> None:
    response = client.post(
        "/recommend",
        json={
            "commodity": {
                "name": "Tomato",
                "category": "fresh_produce",
                "moisture_content_pct": 94.5,
                "fat_content_pct": 0.2,
                "ph": 4.3,
                "respiration_rate_ml_co2_per_kg_hr": 15,
            },
            "requirements": {"desired_shelf_life_days": 14},
            "environment": {
                "storage_type": "chilled",
                "storage_temp_c": 8,
                "relative_humidity_pct": 90,
                "transport_mode": "refrigerated_truck",
                "transport_duration_hr": 24,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "rules-v1"
    assert len(payload["recommendations"]) >= 3
    assert (
        payload["recommendations"][0]["confidence"]
        >= payload["recommendations"][1]["confidence"]
    )
    assert payload["disclaimer"]


def test_invalid_input_is_rejected() -> None:
    response = client.post(
        "/recommend",
        json={
            "commodity": {
                "name": "Rice",
                "category": "dry_staple",
                "moisture_content_pct": 14,
                "fat_content_pct": 1,
                "ph": 20,
            },
            "requirements": {"desired_shelf_life_days": 30},
            "environment": {
                "storage_type": "ambient",
                "storage_temp_c": 25,
                "relative_humidity_pct": 60,
                "transport_mode": "ambient_truck",
                "transport_duration_hr": 12,
            },
        },
    )

    assert response.status_code == 422
