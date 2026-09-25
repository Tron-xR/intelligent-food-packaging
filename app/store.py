from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.schemas import (
    FeedbackInput,
    FeedbackResponse,
    RecommendationRequest,
    RecommendationResponse,
)


class RecommendationNotFoundError(Exception):
    pass


class FeedbackConflictError(Exception):
    pass


class RecommendationStore:
    def __init__(self, database_path: str | Path | None = None) -> None:
        configured_path = database_path or os.getenv(
            "FOOD_PACKAGING_DB",
            str(Path(__file__).parent / "data" / "recommendations.sqlite3"),
        )
        self.database_path = str(configured_path)
        self._lock = Lock()
        self._memory_connection: sqlite3.Connection | None = None
        if self.database_path == ":memory:":
            self._memory_connection = sqlite3.connect(
                self.database_path,
                check_same_thread=False,
            )
        else:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        if self._memory_connection is not None:
            with self._lock:
                try:
                    yield self._memory_connection
                    self._memory_connection.commit()
                except Exception:
                    self._memory_connection.rollback()
                    raise
            return

        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    request_json TEXT NOT NULL,
                    material TEXT NOT NULL,
                    material_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    predicted_shelf_life_days INTEGER NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    recommendation_id TEXT NOT NULL UNIQUE,
                    actual_shelf_life_days INTEGER,
                    outcome_rating TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (recommendation_id) REFERENCES recommendations(
                        recommendation_id
                    )
                );

                CREATE INDEX IF NOT EXISTS idx_recommendations_created_at
                    ON recommendations(created_at);
                CREATE INDEX IF NOT EXISTS idx_feedback_recommendation_id
                    ON feedback(recommendation_id);
                """
            )

    def record_recommendations(
        self,
        request: RecommendationRequest,
        response: RecommendationResponse,
    ) -> RecommendationResponse:
        created_at = _utc_now()
        request_json = request.model_dump_json()
        persisted_recommendations = []
        with self._connection() as connection:
            for recommendation in response.recommendations:
                recommendation_id = uuid4().hex
                persisted = recommendation.model_copy(
                    update={"recommendation_id": recommendation_id}
                )
                connection.execute(
                    """
                    INSERT INTO recommendations (
                        recommendation_id,
                        request_json,
                        material,
                        material_type,
                        confidence,
                        predicted_shelf_life_days,
                        response_json,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        recommendation_id,
                        request_json,
                        persisted.material,
                        persisted.material_type,
                        persisted.confidence,
                        persisted.predicted_shelf_life_days,
                        persisted.model_dump_json(),
                        created_at,
                    ),
                )
                persisted_recommendations.append(persisted)
        return response.model_copy(update={"recommendations": persisted_recommendations})

    def add_feedback(self, feedback: FeedbackInput) -> FeedbackResponse:
        feedback_id = uuid4().hex
        created_at = _utc_now()
        with self._connection() as connection:
            recommendation = connection.execute(
                "SELECT 1 FROM recommendations WHERE recommendation_id = ?",
                (feedback.recommendation_id,),
            ).fetchone()
            if recommendation is None:
                raise RecommendationNotFoundError(feedback.recommendation_id)
            try:
                connection.execute(
                    """
                    INSERT INTO feedback (
                        feedback_id,
                        recommendation_id,
                        actual_shelf_life_days,
                        outcome_rating,
                        notes,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        feedback_id,
                        feedback.recommendation_id,
                        feedback.actual_shelf_life_days,
                        feedback.outcome_rating.value,
                        feedback.notes,
                        created_at,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise FeedbackConflictError(feedback.recommendation_id) from error
        return FeedbackResponse(
            feedback_id=feedback_id,
            recommendation_id=feedback.recommendation_id,
            outcome_rating=feedback.outcome_rating,
            created_at=created_at,
            status="recorded",
        )

    def recommendation_count(self) -> int:
        with self._connection() as connection:
            row = connection.execute("SELECT COUNT(*) FROM recommendations").fetchone()
        return int(row[0])


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
