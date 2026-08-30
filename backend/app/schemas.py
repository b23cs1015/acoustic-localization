from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# =========================================================
# PREDICTION
# =========================================================


class PredictionResult(BaseModel):

    prediction: str

    confidence: Optional[float] = None

    features: Dict[str, float]

    duration_seconds: float

    sample_rate: int


class AnalyzeResponse(BaseModel):

    success: bool

    result: PredictionResult


# =========================================================
# POSITIONS
# =========================================================


class Position(BaseModel):

    id: int

    position_number: int

    name: str

    created_at: str


class PositionResponse(BaseModel):

    success: bool

    position: Position


class PositionsResponse(BaseModel):

    success: bool

    positions: List[Position]


class CreatePositionRequest(BaseModel):

    name: Optional[str] = None


# =========================================================
# MEASUREMENTS
# =========================================================


class Measurement(BaseModel):

    id: int

    timestamp: str

    recording_filename: str

    prediction: str

    confidence: Optional[float] = None

    duration_seconds: float

    sample_rate: int

    features: Dict[str, float]

    # Actual/user-confirmed location
    position_id: Optional[int] = None

    position_number: Optional[int] = None

    position_name: Optional[str] = None

    # Recording conditions
    object_between: Optional[str] = None

    distance_cm: Optional[float] = None

    notes: Optional[str] = None

    # ML feedback
    feedback_correct: Optional[bool] = None

    feedback_timestamp: Optional[str] = None

    # Soft delete
    discarded: bool = False


class MeasurementsResponse(BaseModel):

    success: bool

    count: int

    measurements: List[Measurement]


# =========================================================
# UPDATE MEASUREMENT
# =========================================================


class UpdateMeasurementRequest(BaseModel):

    position_id: Optional[int] = None

    object_between: Optional[str] = None

    distance_cm: Optional[float] = Field(
        default=None,
        ge=0,
    )

    notes: Optional[str] = None


# =========================================================
# FEEDBACK
# =========================================================


class FeedbackRequest(BaseModel):

    # Position the user says is actually correct
    position_id: int

    # True  -> model prediction was correct
    # False -> model prediction was incorrect
    correct: bool