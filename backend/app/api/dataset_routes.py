from __future__ import annotations

import csv
import io
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile
)

from fastapi.responses import StreamingResponse

from ..audio.features import extract_features
from ..audio.preprocessing import load_audio

from ..dataset.models import (
    CreateDatasetPositionRequest,
    DatasetPositionResponse,
    DatasetPositionsResponse,
    DatasetPredictionResponse,
    DatasetSampleResponse,
    DatasetSamplesResponse,
    DatasetSummaryResponse,
    UpdateDatasetSampleRequest
)

from ..dataset.predictor import (
    DatasetPredictor,
    FEATURE_NAMES
)

from ..dataset.storage import (
    RECORDINGS_DIR,
    create_position,
    create_sample,
    delete_sample,
    get_position,
    get_positions,
    get_reference_samples,
    get_sample,
    get_samples,
    get_summary,
    initialize_dataset_database,
    save_prediction,
    update_sample
)


router = APIRouter(
    prefix="/api/dataset",
    tags=["Dataset"]
)


predictor = DatasetPredictor()


# =========================================================
# INITIALIZATION
# =========================================================

initialize_dataset_database()


# =========================================================
# HEALTH
# =========================================================

@router.get(
    "/health"
)
async def dataset_health():

    return {
        "success": True,
        "message":
            "Dataset service is running."
    }


# =========================================================
# POSITIONS
# =========================================================

@router.get(
    "/positions",
    response_model=DatasetPositionsResponse
)
async def dataset_positions():

    return {
        "success": True,
        "positions":
            get_positions()
    }


@router.post(
    "/positions",
    response_model=DatasetPositionResponse
)
async def dataset_create_position(
    request: CreateDatasetPositionRequest
):

    try:

        position = create_position(
            request.name
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    return {
        "success": True,
        "position":
            position
    }


# =========================================================
# CREATE SAMPLE
# =========================================================

@router.post(
    "/samples",
    response_model=DatasetSampleResponse
)
async def create_dataset_sample(
    audio: UploadFile = File(...),

    position_id: Optional[int] = Form(
        default=None
    ),

    target_presence: str = Form(
        ...
    ),

    distance_cm: Optional[float] = Form(
        default=None
    ),

    remarks: Optional[str] = Form(
        default=None
    )
):

    # -----------------------------------------------------
    # Validate target presence
    # -----------------------------------------------------

    valid_target_values = {
        "yes",
        "no",
        "cant_say"
    }

    if target_presence not in valid_target_values:

        raise HTTPException(
            status_code=400,
            detail=(
                "target_presence must be "
                "'yes', 'no', or 'cant_say'."
            )
        )

    # -----------------------------------------------------
    # Validate distance
    # -----------------------------------------------------

    if distance_cm is not None:

        if distance_cm < 0:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Distance cannot be negative."
                )
            )

        allowed_distances = {
            15.0,
            30.0,
            45.0
        }

        if distance_cm not in (
            allowed_distances
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Distance must be "
                    "15, 30, or 45 cm."
                )
            )

    # -----------------------------------------------------
    # Enforce sensible combinations
    # -----------------------------------------------------

    if target_presence == "no":

        distance_cm = None

    elif target_presence == "cant_say":

        distance_cm = None

    # -----------------------------------------------------
    # Position validation
    # -----------------------------------------------------

    if position_id is not None:

        position = get_position(
            position_id
        )

        if position is None:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Selected position "
                    "does not exist."
                )
            )

    # -----------------------------------------------------
    # Validate file
    # -----------------------------------------------------

    original_filename = (
        audio.filename or ""
    )

    if not original_filename.lower().endswith(
        ".wav"
    ):

        raise HTTPException(
            status_code=400,
            detail="Only WAV files are supported."
        )

    # -----------------------------------------------------
    # Temporary file
    # -----------------------------------------------------

    temporary_filename = (
        f".upload_{uuid.uuid4().hex}.wav"
    )

    temporary_path = (
        RECORDINGS_DIR
        / temporary_filename
    )

    final_path: Optional[Path] = None

    try:

        file_data = await audio.read()

        if not file_data:

            raise HTTPException(
                status_code=400,
                detail="Uploaded audio is empty."
            )

        with open(
            temporary_path,
            "wb"
        ) as file:

            file.write(
                file_data
            )

        # -------------------------------------------------
        # Audio loading
        # -------------------------------------------------

        audio_data, sample_rate = (
            load_audio(
                temporary_path,
                target_sample_rate=48000
            )
        )

        if audio_data.size == 0:

            raise HTTPException(
                status_code=400,
                detail="Audio contains no samples."
            )

        duration_seconds = (
            len(audio_data)
            / sample_rate
        )

        # -------------------------------------------------
        # Feature extraction
        # -------------------------------------------------

        features = extract_features(
            audio_data,
            sample_rate
        )

        # -------------------------------------------------
        # Create DB record
        # -------------------------------------------------

        sample = create_sample(
            recording_filename=(
                "pending.wav"
            ),
            position_id=position_id,
            target_presence=(
                target_presence
            ),
            distance_cm=distance_cm,
            remarks=(
                remarks.strip()
                if remarks
                and remarks.strip()
                else None
            ),
            features=features,
            duration_seconds=(
                duration_seconds
            ),
            sample_rate=sample_rate
        )

        sample_id = sample["id"]

        sample_code = sample[
            "sample_code"
        ]

        final_filename = (
            f"{sample_code}.wav"
        )

        final_path = (
            RECORDINGS_DIR
            / final_filename
        )

        os.replace(
            temporary_path,
            final_path
        )

        # -------------------------------------------------
        # Update recording filename
        # -------------------------------------------------

        from ..dataset.storage import (
            get_connection
        )

        connection = get_connection()

        try:

            connection.execute(
                """
                UPDATE samples
                SET recording_filename = ?
                WHERE id = ?
                """,
                (
                    final_filename,
                    sample_id
                )
            )

            connection.commit()

        finally:

            connection.close()

        sample = get_sample(
            sample_id
        )

        return {
            "success": True,
            "sample": sample
        }

    except HTTPException:

        if temporary_path.exists():
            temporary_path.unlink()

        raise

    except Exception as error:

        if temporary_path.exists():
            temporary_path.unlink()

        if final_path is not None:
            if final_path.exists():
                final_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not process audio: {error}"
            )
        )


# =========================================================
# GET SAMPLES
# =========================================================

@router.get(
    "/samples",
    response_model=DatasetSamplesResponse
)
async def dataset_samples():

    samples = get_samples()

    return {
        "success": True,
        "count": len(samples),
        "samples": samples
    }


# =========================================================
# GET SINGLE SAMPLE
# =========================================================

@router.get(
    "/samples/{sample_id}",
    response_model=DatasetSampleResponse
)
async def dataset_sample(
    sample_id: int
):

    sample = get_sample(
        sample_id
    )

    if sample is None:

        raise HTTPException(
            status_code=404,
            detail="Dataset sample not found."
        )

    return {
        "success": True,
        "sample": sample
    }


# =========================================================
# UPDATE SAMPLE
# =========================================================

@router.patch(
    "/samples/{sample_id}",
    response_model=DatasetSampleResponse
)
async def dataset_update_sample(
    sample_id: int,
    request: UpdateDatasetSampleRequest
):

    existing = get_sample(
        sample_id
    )

    if existing is None:

        raise HTTPException(
            status_code=404,
            detail="Dataset sample not found."
        )

    position_id = (
        request.position_id
        if request.position_id is not None
        else existing["position_id"]
    )

    target_presence = (
        request.target_presence
        if request.target_presence is not None
        else existing["target_presence"]
    )

    distance_cm = (
        request.distance_cm
        if request.distance_cm is not None
        else existing["distance_cm"]
    )

    remarks = (
        request.remarks
        if request.remarks is not None
        else existing["remarks"]
    )

    if target_presence == "no":
        distance_cm = None

    elif target_presence == "cant_say":
        distance_cm = None

    if distance_cm is not None:

        if distance_cm not in {
            15.0,
            30.0,
            45.0
        }:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Distance must be "
                    "15, 30, or 45 cm."
                )
            )

    try:

        updated = update_sample(
            sample_id,
            position_id=position_id,
            target_presence=(
                target_presence
            ),
            distance_cm=distance_cm,
            remarks=remarks
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    return {
        "success": True,
        "sample": updated
    }


# =========================================================
# DELETE SAMPLE
# =========================================================

@router.delete(
    "/samples/{sample_id}",
    response_model=DatasetSampleResponse
)
async def dataset_delete_sample(
    sample_id: int
):

    result = delete_sample(
        sample_id
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Dataset sample not found."
        )

    filename = result[
        "recording_filename"
    ]

    if filename:

        recording_path = (
            RECORDINGS_DIR
            / filename
        )

        if recording_path.exists():

            recording_path.unlink()

    return {
        "success": True,
        "sample": result["sample"]
    }


# =========================================================
# AUDIO
# =========================================================

@router.get(
    "/samples/{sample_id}/audio"
)
async def dataset_sample_audio(
    sample_id: int
):

    from fastapi.responses import (
        FileResponse
    )

    sample = get_sample(
        sample_id
    )

    if sample is None:

        raise HTTPException(
            status_code=404,
            detail="Dataset sample not found."
        )

    recording_path = (
        RECORDINGS_DIR
        / sample["recording_filename"]
    )

    if not recording_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Recording file not found."
        )

    return FileResponse(
        recording_path,
        media_type="audio/wav",
        filename=(
            sample["recording_filename"]
        )
    )


# =========================================================
# PREDICT POSITION
# =========================================================

@router.post(
    "/samples/{sample_id}/predict",
    response_model=DatasetPredictionResponse
)
async def predict_dataset_sample(
    sample_id: int
):

    sample = get_sample(
        sample_id
    )

    if sample is None:

        raise HTTPException(
            status_code=404,
            detail="Dataset sample not found."
        )

    # -----------------------------------------------------
    # IMPORTANT:
    #
    # The selected sample is explicitly excluded from
    # the reference dataset.
    #
    # This prevents a sample from matching itself with
    # distance = 0 and producing a meaningless evaluation.
    # -----------------------------------------------------

    reference_samples = (
        get_reference_samples(
            exclude_sample_id=sample_id
        )
    )

    prediction = predictor.predict(
        sample,
        reference_samples
    )

    updated_sample = save_prediction(
        sample_id=sample_id,

        predicted_position_id=(
            prediction[
                "predicted_position_id"
            ]
        ),

        confidence=(
            prediction[
                "confidence"
            ]
        ),

        evaluation=(
            prediction[
                "evaluation"
            ]
        )
    )

    if updated_sample is None:

        raise HTTPException(
            status_code=404,
            detail="Dataset sample not found."
        )

    return {
        "success": True,

        "sample_id":
            sample_id,

        "predicted_position_id":
            prediction[
                "predicted_position_id"
            ],

        "predicted_position_name":
            prediction[
                "predicted_position_name"
            ],

        "confidence":
            prediction[
                "confidence"
            ],

        "ground_truth_position_id":
            sample[
                "position_id"
            ],

        "ground_truth_position_name":
            sample[
                "position_name"
            ],

        "evaluation":
            prediction[
                "evaluation"
            ],

        "nearest_samples":
            prediction[
                "nearest_samples"
            ]
    }


# =========================================================
# PREDICT ALL DATASET SAMPLES
# =========================================================

@router.post(
    "/samples/predict-all"
)
async def predict_all_dataset_samples():

    samples = get_samples()

    labeled_samples = [
        sample
        for sample in samples
        if sample["position_id"] is not None
    ]

    if not labeled_samples:

        return {
            "success": True,
            "total_samples": len(samples),
            "evaluated_samples": 0,
            "skipped_samples": len(samples),
            "correct_predictions": 0,
            "incorrect_predictions": 0,
            "accuracy": None
        }

    correct_predictions = 0
    incorrect_predictions = 0
    skipped_samples = 0

    results = []

    # -----------------------------------------------------
    # Leave-one-out prediction
    #
    # Each sample is excluded from its own reference set.
    # This is the same evaluation methodology used by the
    # offline export script and baseline evaluation.
    # -----------------------------------------------------

    for sample in labeled_samples:

        reference_samples = (
            get_reference_samples(
                exclude_sample_id=sample["id"]
            )
        )

        prediction = predictor.predict(
            sample,
            reference_samples
        )

        evaluation = prediction[
            "evaluation"
        ]

        if evaluation == "correct":

            correct_predictions += 1

        elif evaluation == "incorrect":

            incorrect_predictions += 1

        else:

            skipped_samples += 1

        updated_sample = save_prediction(
            sample_id=sample["id"],

            predicted_position_id=(
                prediction[
                    "predicted_position_id"
                ]
            ),

            confidence=(
                prediction[
                    "confidence"
                ]
            ),

            evaluation=evaluation
        )

        results.append({
            "sample_id":
                sample["id"],

            "sample_code":
                sample["sample_code"],

            "ground_truth_position_id":
                sample["position_id"],

            "ground_truth_position_name":
                sample["position_name"],

            "predicted_position_id":
                prediction[
                    "predicted_position_id"
                ],

            "predicted_position_name":
                prediction[
                    "predicted_position_name"
                ],

            "confidence":
                prediction[
                    "confidence"
                ],

            "evaluation":
                evaluation
        })

    evaluated_samples = (
        correct_predictions
        + incorrect_predictions
    )

    accuracy = None

    if evaluated_samples > 0:

        accuracy = (
            correct_predictions
            / evaluated_samples
        )

    return {
        "success": True,

        "total_samples":
            len(samples),

        "evaluated_samples":
            evaluated_samples,

        "skipped_samples":
            skipped_samples,

        "correct_predictions":
            correct_predictions,

        "incorrect_predictions":
            incorrect_predictions,

        "accuracy":
            accuracy,

        "results":
            results
    }


# =========================================================
# EXPORT HELPERS
# =========================================================

def _csv_response(
    content: str,
    filename: str
) -> StreamingResponse:

    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        }
    )


def _format_csv_value(
    value
) -> str:

    if value is None:
        return ""

    return str(value)


# =========================================================
# EXPORT FEATURE VECTORS
# =========================================================

@router.get(
    "/export/features"
)
async def export_dataset_features():

    samples = get_samples()

    output = io.StringIO(
        newline=""
    )

    writer = csv.writer(
        output
    )

    headers = [
        "sample_id",
        "sample_code",
        "timestamp",
        "position_id",
        "position_name",
        "target_presence",
        "distance_cm",
        "remarks",
        "duration_seconds",
        "sample_rate"
    ]

    headers.extend(
        FEATURE_NAMES
    )

    writer.writerow(
        headers
    )

    exported_rows = 0

    for sample in reversed(samples):

        row = [
            sample["id"],
            sample["sample_code"],
            sample["timestamp"],
            sample["position_id"],
            sample["position_name"],
            sample["target_presence"],
            sample["distance_cm"],
            sample["remarks"],
            sample["duration_seconds"],
            sample["sample_rate"]
        ]

        features = sample[
            "features"
        ]

        for feature_name in FEATURE_NAMES:

            row.append(
                features.get(
                    feature_name,
                    0.0
                )
            )

        writer.writerow(
            [
                _format_csv_value(value)
                for value in row
            ]
        )

        exported_rows += 1

    return _csv_response(
        output.getvalue(),
        "dataset_features.csv"
    )


# =========================================================
# EXPORT PREDICTIONS
# =========================================================

@router.get(
    "/export/predictions"
)
async def export_dataset_predictions():

    samples = get_samples()

    output = io.StringIO(
        newline=""
    )

    writer = csv.writer(
        output
    )

    headers = [
        "sample_id",
        "sample_code",
        "timestamp",

        "ground_truth_position_id",
        "ground_truth_position_name",

        "predicted_position_id",
        "predicted_position_name",

        "confidence",
        "evaluation",
        "prediction_timestamp"
    ]

    for index in range(1, 6):

        headers.extend([
            f"nearest_{index}_sample_id",
            f"nearest_{index}_sample_code",
            f"nearest_{index}_position_name",
            f"nearest_{index}_distance"
        ])

    writer.writerow(
        headers
    )

    # -----------------------------------------------------
    # Export predictions already stored in the database.
    #
    # If Predict All has not been run yet, prediction fields
    # will be empty. This keeps the download faithful to
    # the current dataset state.
    # -----------------------------------------------------

    exported_rows = 0

    for sample in reversed(samples):

        row = [
            sample["id"],
            sample["sample_code"],
            sample["timestamp"],

            sample["position_id"],
            sample["position_name"],

            sample["predicted_position_id"],
            sample["predicted_position_name"],

            sample["prediction_confidence"],
            sample["prediction_evaluation"],
            sample["prediction_timestamp"]
        ]

        # -------------------------------------------------
        # The database stores the final prediction but does
        # not currently store the top-5 nearest neighbours.
        #
        # Recalculate them for export when a prediction
        # exists, using the same leave-one-out procedure.
        # -------------------------------------------------

        nearest_samples = []

        if (
            sample["position_id"] is not None
            and sample["predicted_position_id"] is not None
        ):

            reference_samples = (
                get_reference_samples(
                    exclude_sample_id=sample["id"]
                )
            )

            prediction = predictor.predict(
                sample,
                reference_samples
            )

            nearest_samples = (
                prediction[
                    "nearest_samples"
                ]
            )

        for index in range(5):

            if index < len(
                nearest_samples
            ):

                nearest = (
                    nearest_samples[index]
                )

                row.extend([
                    nearest.get(
                        "sample_id"
                    ),
                    nearest.get(
                        "sample_code"
                    ),
                    nearest.get(
                        "position_name"
                    ),
                    nearest.get(
                        "distance"
                    )
                ])

            else:

                row.extend([
                    "",
                    "",
                    "",
                    ""
                ])

        writer.writerow(
            [
                _format_csv_value(value)
                for value in row
            ]
        )

        exported_rows += 1

    return _csv_response(
        output.getvalue(),
        "dataset_predictions.csv"
    )


# =========================================================
# SUMMARY
# =========================================================

@router.get(
    "/summary",
    response_model=DatasetSummaryResponse
)
async def dataset_summary():

    return {
        "success": True,
        "summary":
            get_summary()
    }