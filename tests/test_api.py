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
    assert all(item["recommendation_id"] for item in payload["recommendations"])
    assert (
        payload["recommendations"][0]["confidence"]
        >= payload["recommendations"][1]["confidence"]
    )
    assert payload["disclaimer"]


def test_feedback_is_linked_to_a_saved_recommendation() -> None:
    recommendation_response = client.post(
        "/recommend",
        json={
            "commodity": {
                "name": "Rice",
                "category": "dry_staple",
                "moisture_content_pct": 14,
                "fat_content_pct": 1,
                "ph": 6.5,
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
    recommendation_id = recommendation_response.json()["recommendations"][0]["recommendation_id"]

    feedback_response = client.post(
        "/feedback",
        json={
            "recommendation_id": recommendation_id,
            "actual_shelf_life_days": 28,
            "outcome_rating": "successful",
            "notes": "Pilot lot remained acceptable through day 28.",
        },
    )

    assert feedback_response.status_code == 201
    assert feedback_response.json()["recommendation_id"] == recommendation_id
    assert feedback_response.json()["status"] == "recorded"

    duplicate_response = client.post(
        "/feedback",
        json={
            "recommendation_id": recommendation_id,
            "outcome_rating": "partial",
        },
    )
    assert duplicate_response.status_code == 409


def test_feedback_for_unknown_recommendation_is_rejected() -> None:
    response = client.post(
        "/feedback",
        json={
            "recommendation_id": "missing",
            "outcome_rating": "unsuccessful",
        },
    )

    assert response.status_code == 404


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
