from fastapi import FastAPI

from app import __version__
from app.engine import recommend
from app.schemas import RecommendationRequest, RecommendationResponse

app = FastAPI(
    title="Intelligent Food Packaging Recommendation API",
    version=__version__,
    description=(
        "Transparent packaging decision-support using food-science-inspired rules and an editable "
        "material knowledge base."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/recommend", response_model=RecommendationResponse)
def recommend_packaging(payload: RecommendationRequest) -> RecommendationResponse:
    return recommend(payload)
