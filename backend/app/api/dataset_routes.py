from __future__ import annotations

import csv
import io
import os
import uuid
from pathlib import Path
from typing import Optional
import math

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from fastapi.responses import (
    FileResponse,
    StreamingResponse,
)

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
    UpdateDatasetSampleRequest,
)

from ..dataset.predictor import (
    DatasetPredictor,
    FEATURE_NAMES,
)

from ..dataset.storage import (
    create_position,
    create_sample,
    delete_sample,
    get_experiment,
    get_experiment_recordings_dir,
    get_position,
    get_positions,
    get_reference_samples,
    get_sample,
    get_samples,
    get_summary,
    initialize_dataset_database,
    save_prediction,
    update_sample,
)


router = APIRouter(
    prefix="/api/dataset",
    tags=["Dataset"],
)


predictor = DatasetPredictor()


# =========================================================
# DEFAULT EXPERIMENT
# =========================================================
#
# EXP-001 is the original 200-sample benchmark.
#
# Keeping this as the default means existing frontend
# requests that do not yet send experiment_id continue to
# work exactly against the original experiment.
# =========================================================

DEFAULT_EXPERIMENT_ID = 1


# =========================================================
# INITIALIZATION
# =========================================================

initialize_dataset_database()


# =========================================================
# EXPERIMENT VALIDATION HELPER
# =========================================================

def _resolve_experiment_id(
    experiment_id: Optional[int],
) -> int:
    """
    Resolve the requested experiment.

    If experiment_id is omitted, EXP-001 is used for
    backwards compatibility.

    The returned experiment is also validated.
    """

    resolved_id = (
        experiment_id
        if experiment_id is not None
        else DEFAULT_EXPERIMENT_ID
    )

    try:

        experiment = get_experiment(
            resolved_id
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not access experiment "
                f"{resolved_id}: {error}"
            ),
        )

    if experiment is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Experiment {resolved_id} "
                "does not exist."
            ),
        )

    return resolved_id


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
            "Dataset service is running.",

        "default_experiment_id":
            DEFAULT_EXPERIMENT_ID,
    }


# =========================================================
# POSITIONS
# =========================================================

@router.get(
    "/positions",
    response_model=DatasetPositionsResponse,
)
async def dataset_positions(
    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    return {
        "success": True,

        "positions":
            get_positions(
                experiment_id=
                    resolved_experiment_id
            ),
    }


# =========================================================
# CREATE POSITION
# =========================================================

@router.post(
    "/positions",
    response_model=DatasetPositionResponse,
)
async def dataset_create_position(
    request: CreateDatasetPositionRequest,
    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    try:

        position = create_position(
            request.name,
            experiment_id=
                resolved_experiment_id,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return {
        "success": True,

        "position":
            position,
    }


# =========================================================
# CREATE SAMPLE
# =========================================================

@router.post(
    "/samples",
    response_model=DatasetSampleResponse,
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
    ),

    experiment_id: Optional[int] = Form(
        default=None
    ),
):

    # -----------------------------------------------------
    # Resolve experiment.
    # -----------------------------------------------------

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    # -----------------------------------------------------
    # Validate target presence.
    # -----------------------------------------------------

    valid_target_values = {
        "yes",
        "no",
        "cant_say",
    }

    if target_presence not in valid_target_values:

        raise HTTPException(
            status_code=400,
            detail=(
                "target_presence must be "
                "'yes', 'no', or 'cant_say'."
            ),
        )

    # -----------------------------------------------------
    # Validate distance.
    #
    # Distance is intentionally arbitrary.
    #
    # Any finite positive value in centimetres is accepted.
    # Examples:
    #   15
    #   27.5
    #   32.75
    #   45
    #   100
    # -----------------------------------------------------

    if distance_cm is not None:

        if (
            not math.isfinite(distance_cm)
            or distance_cm <= 0
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "distance_cm must be a finite "
                    "value greater than 0 cm."
                ),
            )

    # -----------------------------------------------------
    # Enforce sensible combinations.
    # -----------------------------------------------------

    if target_presence in {
        "no",
        "cant_say",
    }:

        distance_cm = None

    # -----------------------------------------------------
    # Position validation.
    #
    # IMPORTANT:
    #
    # Position must belong to the selected experiment.
    # -----------------------------------------------------

    if position_id is not None:

        position = get_position(
            position_id,
            experiment_id=
                resolved_experiment_id,
        )

        if position is None:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Selected position does not exist "
                    "in the selected experiment."
                ),
            )

    # -----------------------------------------------------
    # Validate file.
    # -----------------------------------------------------

    original_filename = (
        audio.filename or ""
    )

    if not original_filename.lower().endswith(
        ".wav"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Only WAV files are supported."
            ),
        )

    # -----------------------------------------------------
    # Experiment recording directory.
    # -----------------------------------------------------

    recordings_dir = (
        get_experiment_recordings_dir(
            resolved_experiment_id
        )
    )

    # -----------------------------------------------------
    # Temporary file.
    # -----------------------------------------------------
    #
    # Temporary uploads are placed directly inside the
    # selected experiment's recording directory.
    # -----------------------------------------------------

    temporary_filename = (
        f".upload_{uuid.uuid4().hex}.wav"
    )

    temporary_path = (
        recordings_dir
        / temporary_filename
    )

    final_path: Optional[Path] = None

    try:

        # -------------------------------------------------
        # Read uploaded file.
        # -------------------------------------------------

        file_data = await audio.read()

        if not file_data:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Uploaded audio is empty."
                ),
            )

        with open(
            temporary_path,
            "wb",
        ) as file:

            file.write(
                file_data
            )

        # -------------------------------------------------
        # Audio loading.
        # -------------------------------------------------

        audio_data, sample_rate = (
            load_audio(
                temporary_path,
                target_sample_rate=48000,
            )
        )

        if audio_data.size == 0:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Audio contains no samples."
                ),
            )

        duration_seconds = (
            len(audio_data)
            / sample_rate
        )

        # -------------------------------------------------
        # Feature extraction.
        # -------------------------------------------------

        features = extract_features(
            audio_data,
            sample_rate,
        )

        # -------------------------------------------------
        # Create database record.
        #
        # The temporary recording name is stored initially.
        # It is replaced with AL-XXXX.wav after the sample
        # ID is generated.
        # -------------------------------------------------

        sample = create_sample(
            recording_filename="pending.wav",

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

            sample_rate=sample_rate,

            experiment_id=
                resolved_experiment_id,
        )

        sample_id = sample["id"]

        sample_code = sample[
            "sample_code"
        ]

        # -------------------------------------------------
        # Final recording filename.
        # -------------------------------------------------

        final_filename = (
            f"{sample_code}.wav"
        )

        final_path = (
            recordings_dir
            / final_filename
        )

        # -------------------------------------------------
        # Move temporary file to final location.
        # -------------------------------------------------

        os.replace(
            temporary_path,
            final_path,
        )

        # -------------------------------------------------
        # Update recording filename.
        # -------------------------------------------------

        from ..dataset.storage import (
            get_connection,
        )

        connection = get_connection()

        try:

            connection.execute(
                """
                UPDATE samples
                SET recording_filename = ?
                WHERE id = ?
                  AND experiment_id = ?
                """,
                (
                    final_filename,
                    sample_id,
                    resolved_experiment_id,
                ),
            )

            connection.commit()

        finally:

            connection.close()

        # -------------------------------------------------
        # Fetch updated sample.
        # -------------------------------------------------

        sample = get_sample(
            sample_id,
            experiment_id=
                resolved_experiment_id,
        )

        return {
            "success": True,

            "sample":
                sample,
        }

    except HTTPException:

        if temporary_path.exists():

            temporary_path.unlink()

        raise

    except Exception as error:

        if temporary_path.exists():

            temporary_path.unlink()

        if (
            final_path is not None
            and final_path.exists()
        ):

            final_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not process audio: {error}"
            ),
        )


# =========================================================
# GET SAMPLES
# =========================================================

@router.get(
    "/samples",
    response_model=DatasetSamplesResponse,
)
async def dataset_samples(
    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    samples = get_samples(
        experiment_id=
            resolved_experiment_id
    )

    return {
        "success": True,

        "count":
            len(samples),

        "samples":
            samples,
    }


# =========================================================
# GET SINGLE SAMPLE
# =========================================================

@router.get(
    "/samples/{sample_id}",
    response_model=DatasetSampleResponse,
)
async def dataset_sample(
    sample_id: int,

    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    sample = get_sample(
        sample_id,
        experiment_id=
            resolved_experiment_id,
    )

    if sample is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Dataset sample not found "
                "in the selected experiment."
            ),
        )

    return {
        "success": True,

        "sample":
            sample,
    }


# =========================================================
# UPDATE SAMPLE
# =========================================================

@router.patch(
    "/samples/{sample_id}",
    response_model=DatasetSampleResponse,
)
async def dataset_update_sample(
    sample_id: int,

    request: UpdateDatasetSampleRequest,

    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    existing = get_sample(
        sample_id,
        experiment_id=
            resolved_experiment_id,
    )

    if existing is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Dataset sample not found "
                "in the selected experiment."
            ),
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

    # -----------------------------------------------------
    # Validate target presence.
    # -----------------------------------------------------

    valid_target_values = {
        "yes",
        "no",
        "cant_say",
    }

    if target_presence not in valid_target_values:

        raise HTTPException(
            status_code=400,
            detail=(
                "target_presence must be "
                "'yes', 'no', or 'cant_say'."
            ),
        )

    # -----------------------------------------------------
    # Enforce target/distance relationship.
    # -----------------------------------------------------

    if target_presence in {
        "no",
        "cant_say",
    }:

        distance_cm = None

    # -----------------------------------------------------
    # Validate distance.
    #
    # Any finite positive distance in centimetres is valid.
    # -----------------------------------------------------

    if distance_cm is not None:

        if (
            not math.isfinite(distance_cm)
            or distance_cm <= 0
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "distance_cm must be a finite "
                    "value greater than 0 cm."
                ),
            )

    # -----------------------------------------------------
    # Validate position.
    # -----------------------------------------------------

    if position_id is not None:

        position = get_position(
            position_id,
            experiment_id=
                resolved_experiment_id,
        )

        if position is None:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Selected position does not exist "
                    "in the selected experiment."
                ),
            )

    try:

        updated = update_sample(
            sample_id,

            position_id=
                position_id,

            target_presence=(
                target_presence
            ),

            distance_cm=
                distance_cm,

            remarks=
                remarks,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return {
        "success": True,

        "sample":
            updated,
    }


# =========================================================
# DELETE SAMPLE
# =========================================================

@router.delete(
    "/samples/{sample_id}",
    response_model=DatasetSampleResponse,
)
async def dataset_delete_sample(
    sample_id: int,

    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    existing = get_sample(
        sample_id,
        experiment_id=
            resolved_experiment_id,
    )

    if existing is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Dataset sample not found "
                "in the selected experiment."
            ),
        )

    result = delete_sample(
        sample_id
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Dataset sample not found.",
        )

    filename = result[
        "recording_filename"
    ]

    if filename:

        recording_path = (
            get_experiment_recordings_dir(
                resolved_experiment_id
            )
            / filename
        )

        if recording_path.exists():

            recording_path.unlink()

        else:

            # ------------------------------------------------
            # Backwards compatibility:
            #
            # Existing EXP-001 recordings may still be in
            # the legacy recordings directory before the
            # migration copy is completed.
            # ------------------------------------------------

            from ..dataset.storage import (
                LEGACY_RECORDINGS_DIR,
            )

            legacy_path = (
                LEGACY_RECORDINGS_DIR
                / filename
            )

            if legacy_path.exists():

                legacy_path.unlink()

    return {
        "success": True,

        "sample":
            result["sample"],
    }


# =========================================================
# AUDIO
# =========================================================

@router.get(
    "/samples/{sample_id}/audio"
)
async def dataset_sample_audio(
    sample_id: int,

    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    sample = get_sample(
        sample_id,
        experiment_id=
            resolved_experiment_id,
    )

    if sample is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Dataset sample not found "
                "in the selected experiment."
            ),
        )

    filename = sample[
        "recording_filename"
    ]

    if not filename:

        raise HTTPException(
            status_code=404,
            detail=(
                "This sample has no recording."
            ),
        )

    recording_path = (
        get_experiment_recordings_dir(
            resolved_experiment_id
        )
        / filename
    )

    # -----------------------------------------------------
    # Backwards compatibility for EXP-001.
    # -----------------------------------------------------

    if not recording_path.exists():

        from ..dataset.storage import (
            LEGACY_RECORDINGS_DIR,
        )

        legacy_path = (
            LEGACY_RECORDINGS_DIR
            / filename
        )

        if legacy_path.exists():

            recording_path = legacy_path

    if not recording_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Recording file not found.",
        )

    return FileResponse(
        recording_path,

        media_type="audio/wav",

        filename=filename,
    )


# =========================================================
# PREDICT POSITION
# =========================================================

@router.post(
    "/samples/{sample_id}/predict",
    response_model=DatasetPredictionResponse,
)
async def predict_dataset_sample(
    sample_id: int,

    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    sample = get_sample(
        sample_id,
        experiment_id=
            resolved_experiment_id,
    )

    if sample is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Dataset sample not found "
                "in the selected experiment."
            ),
        )

    # -----------------------------------------------------
    # IMPORTANT:
    #
    # Reference samples are restricted to the same
    # experiment.
    #
    # The current sample is excluded for leave-one-out
    # evaluation.
    # -----------------------------------------------------

    reference_samples = (
        get_reference_samples(
            experiment_id=
                resolved_experiment_id,

            exclude_sample_id=
                sample_id,
        )
    )

    if not reference_samples:

        raise HTTPException(
            status_code=400,
            detail=(
                "No reference samples are available "
                "in the selected experiment."
            ),
        )

    prediction = predictor.predict(
        sample,
        reference_samples,
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
        ),
    )

    if updated_sample is None:

        raise HTTPException(
            status_code=404,
            detail="Dataset sample not found.",
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
            ],
    }


# =========================================================
# PREDICT ALL DATASET SAMPLES
# =========================================================

@router.post(
    "/samples/predict-all"
)
async def predict_all_dataset_samples(
    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    samples = get_samples(
        experiment_id=
            resolved_experiment_id
    )

    labeled_samples = [
        sample
        for sample in samples
        if sample["position_id"] is not None
        and sample.get("features") is not None
    ]

    if not labeled_samples:

        return {
            "success": True,

            "experiment_id":
                resolved_experiment_id,

            "total_samples":
                len(samples),

            "evaluated_samples":
                0,

            "skipped_samples":
                len(samples),

            "correct_predictions":
                0,

            "incorrect_predictions":
                0,

            "accuracy":
                None,

            "results":
                [],
        }

    correct_predictions = 0

    incorrect_predictions = 0

    skipped_samples = 0

    results = []

    # -----------------------------------------------------
    # Leave-one-out prediction.
    #
    # Every sample uses ONLY reference samples from the
    # selected experiment.
    # -----------------------------------------------------

    for sample in labeled_samples:

        reference_samples = (
            get_reference_samples(
                experiment_id=
                    resolved_experiment_id,

                exclude_sample_id=
                    sample["id"],
            )
        )

        if not reference_samples:

            skipped_samples += 1

            continue

        prediction = predictor.predict(
            sample,
            reference_samples,
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

        save_prediction(
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

            evaluation=evaluation,
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
                evaluation,
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

        "experiment_id":
            resolved_experiment_id,

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
            results,
    }


# =========================================================
# EXPORT HELPERS
# =========================================================

def _csv_response(
    content: str,
    filename: str,
) -> StreamingResponse:

    return StreamingResponse(
        iter([content]),

        media_type="text/csv",

        headers={
            "Content-Disposition":
                (
                    f'attachment; '
                    f'filename="{filename}"'
                )
        },
    )


def _format_csv_value(
    value,
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
async def export_dataset_features(
    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    samples = get_samples(
        experiment_id=
            resolved_experiment_id
    )

    output = io.StringIO(
        newline=""
    )

    writer = csv.writer(
        output
    )

    headers = [
        "experiment_id",

        "sample_id",

        "sample_code",

        "timestamp",

        "recording_filename",

        "position_id",

        "position_name",

        "target_presence",

        "distance_cm",

        "remarks",

        "duration_seconds",

        "sample_rate",
    ]

    headers.extend(
        FEATURE_NAMES
    )

    writer.writerow(
        headers
    )

    for sample in reversed(samples):

        row = [
            resolved_experiment_id,

            sample["id"],

            sample["sample_code"],

            sample["timestamp"],

            sample["recording_filename"],

            sample["position_id"],

            sample["position_name"],

            sample["target_presence"],

            sample["distance_cm"],

            sample["remarks"],

            sample["duration_seconds"],

            sample["sample_rate"],
        ]

        features = (
            sample.get("features")
            or {}
        )

        for feature_name in FEATURE_NAMES:

            row.append(
                features.get(
                    feature_name,
                    0.0,
                )
            )

        writer.writerow(
            [
                _format_csv_value(
                    value
                )
                for value in row
            ]
        )

    filename = (
        f"dataset_features_"
        f"EXP-{resolved_experiment_id:03d}.csv"
    )

    return _csv_response(
        output.getvalue(),
        filename,
    )


# =========================================================
# EXPORT PREDICTIONS
# =========================================================

@router.get(
    "/export/predictions"
)
async def export_dataset_predictions(
    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    samples = get_samples(
        experiment_id=
            resolved_experiment_id
    )

    output = io.StringIO(
        newline=""
    )

    writer = csv.writer(
        output
    )

    headers = [
        "experiment_id",

        "sample_id",

        "sample_code",

        "timestamp",

        "ground_truth_position_id",

        "ground_truth_position_name",

        "predicted_position_id",

        "predicted_position_name",

        "confidence",

        "evaluation",

        "prediction_timestamp",
    ]

    for index in range(1, 6):

        headers.extend([
            f"nearest_{index}_sample_id",

            f"nearest_{index}_sample_code",

            f"nearest_{index}_position_name",

            f"nearest_{index}_distance",
        ])

    writer.writerow(
        headers
    )

    for sample in reversed(samples):

        row = [
            resolved_experiment_id,

            sample["id"],

            sample["sample_code"],

            sample["timestamp"],

            sample["position_id"],

            sample["position_name"],

            sample["predicted_position_id"],

            sample["predicted_position_name"],

            sample["prediction_confidence"],

            sample["prediction_evaluation"],

            sample["prediction_timestamp"],
        ]

        nearest_samples = []

        if (
            sample["position_id"] is not None
            and
            sample["predicted_position_id"]
            is not None
            and
            sample.get("features") is not None
        ):

            reference_samples = (
                get_reference_samples(
                    experiment_id=
                        resolved_experiment_id,

                    exclude_sample_id=
                        sample["id"],
                )
            )

            if reference_samples:

                prediction = predictor.predict(
                    sample,
                    reference_samples,
                )

                nearest_samples = (
                    prediction.get(
                        "nearest_samples",
                        [],
                    )
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
                    ),
                ])

            else:

                row.extend([
                    "",
                    "",
                    "",
                    "",
                ])

        writer.writerow(
            [
                _format_csv_value(
                    value
                )
                for value in row
            ]
        )

    filename = (
        f"dataset_predictions_"
        f"EXP-{resolved_experiment_id:03d}.csv"
    )

    return _csv_response(
        output.getvalue(),
        filename,
    )


# =========================================================
# SUMMARY
# =========================================================

@router.get(
    "/summary",
    response_model=DatasetSummaryResponse,
)
async def dataset_summary(
    experiment_id: Optional[int] = None,
):

    resolved_experiment_id = (
        _resolve_experiment_id(
            experiment_id
        )
    )

    return {
        "success": True,

        "summary":
            get_summary(
                experiment_id=
                    resolved_experiment_id
            ),
    }