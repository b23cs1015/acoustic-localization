from typing import Dict, List, Optional, Literal

from pydantic import BaseModel, Field


# =========================================================
# DATASET LABELS
# =========================================================

TargetPresence = Literal[
    "yes",
    "no",
    "cant_say"
]

PredictionEvaluation = Literal[
    "correct",
    "incorrect",
    "not_evaluable"
]


# =========================================================
# POSITIONS
# =========================================================

class DatasetPosition(BaseModel):
    id: int
    position_number: int
    name: str
    created_at: str


class DatasetPositionResponse(BaseModel):
    success: bool
    position: DatasetPosition


class DatasetPositionsResponse(BaseModel):
    success: bool
    positions: List[DatasetPosition]


# =========================================================
# SAMPLE
# =========================================================

class DatasetSample(BaseModel):
    id: int

    sample_code: str

    timestamp: str

    recording_filename: str

    position_id: Optional[int] = None

    position_name: Optional[str] = None

    target_presence: TargetPresence

    distance_cm: Optional[float] = Field(
        default=None,
        ge=0
    )

    remarks: Optional[str] = None

    features: Dict[str, float]

    duration_seconds: float

    sample_rate: int

    # -----------------------------------------------------
    # Prediction
    # -----------------------------------------------------

    predicted_position_id: Optional[int] = None

    predicted_position_name: Optional[str] = None

    prediction_confidence: Optional[float] = None

    prediction_evaluation: Optional[
        PredictionEvaluation
    ] = None

    prediction_timestamp: Optional[str] = None


class DatasetSamplesResponse(BaseModel):
    success: bool
    count: int
    samples: List[DatasetSample]


class DatasetSampleResponse(BaseModel):
    success: bool
    sample: DatasetSample


# =========================================================
# CREATE / UPDATE
# =========================================================

class CreateDatasetPositionRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100
    )


class UpdateDatasetSampleRequest(BaseModel):
    position_id: Optional[int] = None

    target_presence: Optional[
        TargetPresence
    ] = None

    distance_cm: Optional[float] = Field(
        default=None,
        ge=0
    )

    remarks: Optional[str] = None


# =========================================================
# PREDICTION
# =========================================================

class NearestDatasetSample(BaseModel):
    sample_id: int

    sample_code: str

    position_name: Optional[str] = None

    distance: float


class DatasetPredictionResponse(BaseModel):
    success: bool

    sample_id: int

    predicted_position_id: Optional[int] = None

    predicted_position_name: Optional[str] = None

    confidence: Optional[float] = None

    ground_truth_position_id: Optional[int] = None

    ground_truth_position_name: Optional[str] = None

    evaluation: PredictionEvaluation

    nearest_samples: List[
        NearestDatasetSample
    ]


# =========================================================
# SUMMARY
# =========================================================

class DatasetSummary(BaseModel):
    total_samples: int

    labeled_samples: int

    evaluable_predictions: int

    correct_predictions: int

    incorrect_predictions: int

    accuracy: Optional[float] = None

    positions: Dict[str, int]

    target_presence: Dict[str, int]

    distances: Dict[str, int]


class DatasetSummaryResponse(BaseModel):
    success: bool
    summary: DatasetSummary