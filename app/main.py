from typing import Annotated, cast

from fastapi import Depends, FastAPI, HTTPException, status

from app import __version__
from app.engine import recommend
from app.schemas import (
    FeedbackInput,
    FeedbackResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.store import FeedbackConflictError, RecommendationNotFoundError, RecommendationStore

app = FastAPI(
    title="Intelligent Food Packaging Recommendation API",
    version=__version__,
    description=(
        "Transparent packaging decision-support using food-science-inspired rules and an editable "
        "material knowledge base."
    ),
)
app.state.store = RecommendationStore()


def get_store() -> RecommendationStore:
    return cast(RecommendationStore, app.state.store)


StoreDependency = Annotated[RecommendationStore, Depends(get_store)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/recommend", response_model=RecommendationResponse)
def recommend_packaging(
    payload: RecommendationRequest,
    store: StoreDependency,
) -> RecommendationResponse:
    response = recommend(payload)
    return store.record_recommendations(payload, response)


@app.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def record_feedback(
    payload: FeedbackInput,
    store: StoreDependency,
) -> FeedbackResponse:
    try:
        return store.add_feedback(payload)
    except RecommendationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {payload.recommendation_id} was not found.",
        ) from error
    except FeedbackConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback has already been recorded for this recommendation.",
        ) from error
