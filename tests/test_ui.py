import importlib.util
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.main import app as api_app

spec = importlib.util.spec_from_file_location("packaging_ui", Path(__file__).parents[1] / "app.py")
assert spec is not None and spec.loader is not None
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)


def sample_payload() -> dict[str, Any]:
    return ui.build_request_payload(
        commodity_name="Tomato",
        category="fresh_produce",
        desired_shelf_life=14,
        moisture=94.5,
        fat_content=0.2,
        ph_level=4.3,
        respiration=15.0,
        storage_type="chilled",
        storage_temp_c=8.0,
        relative_humidity_pct=90.0,
        transport_mode="refrigerated_truck",
        transport_duration_hr=24.0,
    )


def test_ui_payload_is_accepted_by_recommendation_api() -> None:
    response = TestClient(api_app).post("/recommend", json=sample_payload())

    assert response.status_code == 200
    result = response.json()
    assert result["recommendations"]


def test_fetch_recommendation_uses_configured_api_endpoint(monkeypatch: Any) -> None:
    response = Mock()
    response.json.return_value = {"recommendations": [], "warnings": []}
    calls: list[tuple[str, dict[str, Any], tuple[int, int]]] = []

    def fake_post(
        url: str,
        *,
        json: dict[str, Any],
        timeout: tuple[int, int],
    ) -> Mock:
        calls.append((url, json, timeout))
        return response

    monkeypatch.setattr(ui.requests, "post", fake_post)
    payload = sample_payload()

    result = ui.fetch_recommendation(payload)

    assert result == {"recommendations": [], "warnings": []}
    assert calls == [(f"{ui.API_BASE_URL}/recommend", payload, (5, 30))]
    response.raise_for_status.assert_called_once_with()


def test_qr_payload_contains_recommendation_traceability() -> None:
    request_payload = sample_payload()
    recommendation_response = {
        "recommendations": [{"recommendation_id": "rec-123"}],
        "model_version": "rules-v1",
        "disclaimer": "Engineering starting point.",
    }

    qr_payload = ui._qr_payload(request_payload, recommendation_response)
    qr_image = ui.generate_qr(qr_payload)

    assert qr_payload["recommendation_ids"] == ["rec-123"]
    assert qr_image.startswith(b"\x89PNG\r\n\x1a\n")
