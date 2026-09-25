from pathlib import Path

import pytest

from app.engine import recommend
from app.schemas import (
    CommodityCategory,
    CommodityInput,
    EnvironmentInput,
    FeedbackInput,
    OutcomeRating,
    RecommendationRequest,
    RequirementsInput,
    StorageType,
)
from app.store import FeedbackConflictError, RecommendationStore


def make_request() -> RecommendationRequest:
    return RecommendationRequest(
        commodity=CommodityInput(
            name="Milk",
            category=CommodityCategory.DAIRY,
            moisture_content_pct=87,
            fat_content_pct=3.5,
            ph=6.6,
        ),
        requirements=RequirementsInput(desired_shelf_life_days=10),
        environment=EnvironmentInput(
            storage_type=StorageType.CHILLED,
            storage_temp_c=4,
            relative_humidity_pct=75,
            transport_mode="refrigerated_truck",
            transport_duration_hr=12,
        ),
    )


def test_sqlite_store_persists_recommendations_and_feedback(tmp_path: Path) -> None:
    store = RecommendationStore(tmp_path / "recommendations.sqlite3")
    response = store.record_recommendations(make_request(), recommend(make_request()))

    assert store.recommendation_count() == len(response.recommendations)
    recommendation_id = response.recommendations[0].recommendation_id
    assert recommendation_id is not None

    feedback = store.add_feedback(
        FeedbackInput(
            recommendation_id=recommendation_id,
            actual_shelf_life_days=9,
            outcome_rating=OutcomeRating.SUCCESSFUL,
        )
    )
    assert feedback.status == "recorded"

    with pytest.raises(FeedbackConflictError):
        store.add_feedback(
            FeedbackInput(
                recommendation_id=recommendation_id,
                outcome_rating=OutcomeRating.PARTIAL,
            )
        )
