import shutil
import tempfile

from pathlib import Path

from ..analytics import (
    get_distance_analysis,
    get_feature_data,
    get_object_analysis,
    get_pca_analysis,
    get_position_analysis,
    get_summary,
)

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)

from fastapi.responses import FileResponse

from ..audio.features import (
    extract_features,
)

from ..audio.preprocessing import (
    load_audio,
)

from ..ml.predictor import (
    Predictor,
)

from ..ml.distance_predictor import (
    DistancePredictor,
)

from ..schemas import (
    AnalyzeResponse,
    PredictionResult,
    MeasurementsResponse,
    PositionsResponse,
    PositionResponse,
    CreatePositionRequest,
    UpdateMeasurementRequest,
    FeedbackRequest,
)

from ..storage import (
    RECORDINGS_DIR,
    create_position,
    get_measurement,
    get_measurements,
    get_position,
    get_positions,
    save_measurement,
    set_measurement_discarded,
    update_measurement,
    update_measurement_feedback,
)


router = APIRouter(
    prefix="/api",
)


predictor = Predictor()

# Separate regression model for distance estimation.
# The existing position KNN predictor remains unchanged.
distance_predictor = DistancePredictor()


# =========================================================
# HEALTH
# =========================================================


@router.get("/health")
async def health():

    return {
        "status": "ok",
        "service": "acoustic-localization",
    }


# =========================================================
# ANALYTICS DASHBOARD
# =========================================================


@router.get(
    "/analytics",
)
async def analytics():

    return {
        "success": True,

        "summary": get_summary(),

        **get_feature_data(),

        "position": get_position_analysis(),

        "distance": get_distance_analysis(),

        "object": get_object_analysis(),

        "pca": get_pca_analysis(),
    }


@router.get(
    "/analytics/summary",
)
async def analytics_summary():

    return {
        "success": True,
        "summary": get_summary(),
    }


@router.get(
    "/analytics/features",
)
async def analytics_features():

    return {
        "success": True,
        **get_feature_data(),
    }


@router.get(
    "/analytics/position",
)
async def analytics_position():

    return {
        "success": True,
        **get_position_analysis(),
    }


@router.get(
    "/analytics/distance",
)
async def analytics_distance():

    return {
        "success": True,
        **get_distance_analysis(),
    }


@router.get(
    "/analytics/object",
)
async def analytics_object():

    return {
        "success": True,
        **get_object_analysis(),
    }


@router.get(
    "/analytics/pca",
)
async def analytics_pca():

    return {
        "success": True,
        **get_pca_analysis(),
    }


# =========================================================
# ANALYZE AUDIO
# =========================================================


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
)
async def analyze_audio(
    audio: UploadFile = File(...),
):

    if not audio.filename:

        raise HTTPException(
            status_code=400,
            detail="No audio file provided.",
        )

    if audio.content_type not in {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "application/octet-stream",
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported audio format. "
                "Please send WAV audio."
            ),
        )

    data = await audio.read()

    if len(data) == 0:

        raise HTTPException(
            status_code=400,
            detail="Uploaded audio is empty.",
        )

    temporary_path = None

    try:

        # ---------------------------------------------
        # Temporary WAV
        # ---------------------------------------------

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        ) as temporary_file:

            temporary_file.write(data)

            temporary_path = Path(
                temporary_file.name
            )

        # ---------------------------------------------
        # Load audio
        # ---------------------------------------------

        signal, sample_rate = load_audio(
            temporary_path,
            target_sample_rate=48000,
        )

        duration = (
            len(signal)
            / sample_rate
        )

        # ---------------------------------------------
        # Extract acoustic fingerprint
        # ---------------------------------------------

        features = extract_features(
            signal,
            sample_rate,
        )

        # ---------------------------------------------
        # ML prediction
        # ---------------------------------------------
        #
        # The predictor only uses previously confirmed
        # recordings from the current application.
        #
        # Task 1 CSV data is not loaded here.
        # ---------------------------------------------

        prediction, confidence = (
            predictor.predict(
                features
            )
        )

        # ---------------------------------------------
        # Distance prediction
        # ---------------------------------------------
        #
        # This is a supervised regression estimate based
        # on the 12 acoustic features and EXP-013 training
        # data. It is separate from position localization.
        # ---------------------------------------------

        try:

            predicted_distance_cm = (
                distance_predictor.predict(
                    features
                )
            )

        except Exception as distance_error:

            # Keep the position measurement working even
            # if the optional distance model is unavailable.
            predicted_distance_cm = None

            print(
                "Distance prediction unavailable:",
                distance_error,
            )

        # ---------------------------------------------
        # Generate unique recording number
        # ---------------------------------------------

        existing_measurements = (
            get_measurements(
                include_discarded=True
            )
        )

        measurement_number = (
            len(existing_measurements)
            + 1
        )

        recording_filename = (
            f"measurement_"
            f"{measurement_number:06d}.wav"
        )

        permanent_recording_path = (
            RECORDINGS_DIR
            / recording_filename
        )

        # ---------------------------------------------
        # Save permanent WAV
        # ---------------------------------------------

        shutil.copy2(
            temporary_path,
            permanent_recording_path,
        )

        # ---------------------------------------------
        # Save measurement metadata
        # ---------------------------------------------

        measurement_id = save_measurement(
            recording_filename=recording_filename,
            prediction=prediction,
            confidence=confidence,
            duration_seconds=duration,
            sample_rate=sample_rate,
            features=features,
            predicted_distance_cm=(
                predicted_distance_cm
            ),
        )

        # ---------------------------------------------
        # Build response
        # ---------------------------------------------

        result = PredictionResult(
            prediction=prediction,
            confidence=confidence,
            predicted_distance_cm=(
                predicted_distance_cm
            ),
            features=features,
            duration_seconds=duration,
            sample_rate=sample_rate,
        )

        return AnalyzeResponse(
            success=True,
            measurement_id=measurement_id,
            result=result,
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Audio processing failed: "
                f"{str(error)}"
            ),
        )

    finally:

        if (
            temporary_path
            and temporary_path.exists()
        ):

            temporary_path.unlink()


# =========================================================
# POSITIONS
# =========================================================


@router.get(
    "/positions",
    response_model=PositionsResponse,
)
async def positions():

    return {
        "success": True,
        "positions": get_positions(),
    }


@router.post(
    "/positions",
    response_model=PositionResponse,
)
async def add_position(
    request: CreatePositionRequest,
):

    try:

        position = create_position(
            request.name
        )

        return {
            "success": True,
            "position": position,
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not create position: "
                f"{str(error)}"
            ),
        )


# =========================================================
# MEASUREMENT HISTORY
# =========================================================


@router.get(
    "/measurements",
    response_model=MeasurementsResponse,
)
async def measurements():

    data = get_measurements()

    return {
        "success": True,
        "count": len(data),
        "measurements": data,
    }


# =========================================================
# SINGLE MEASUREMENT
# =========================================================


@router.get(
    "/measurements/{measurement_id}",
)
async def measurement(
    measurement_id: int,
):

    result = get_measurement(
        measurement_id
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Measurement not found.",
        )

    return {
        "success": True,
        "measurement": result,
    }


# =========================================================
# UPDATE MEASUREMENT DETAILS
# =========================================================


@router.patch(
    "/measurements/{measurement_id}",
)
async def edit_measurement(
    measurement_id: int,
    request: UpdateMeasurementRequest,
):

    existing_measurement = get_measurement(
        measurement_id
    )

    if existing_measurement is None:

        raise HTTPException(
            status_code=404,
            detail="Measurement not found.",
        )

    if request.position_id is not None:

        position = get_position(
            request.position_id
        )

        if position is None:

            raise HTTPException(
                status_code=404,
                detail="Position not found.",
            )

    result = update_measurement(
        measurement_id=measurement_id,
        position_id=request.position_id,
        object_between=request.object_between,
        distance_cm=request.distance_cm,
        notes=request.notes,
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Measurement not found.",
        )

    return {
        "success": True,
        "measurement": result,
    }


# =========================================================
# FEEDBACK
# =========================================================


@router.post(
    "/measurements/{measurement_id}/feedback",
)
async def measurement_feedback(
    measurement_id: int,
    request: FeedbackRequest,
):

    # ---------------------------------------------
    # Check measurement
    # ---------------------------------------------

    existing_measurement = get_measurement(
        measurement_id
    )

    if existing_measurement is None:

        raise HTTPException(
            status_code=404,
            detail="Measurement not found.",
        )

    # ---------------------------------------------
    # Check position
    # ---------------------------------------------

    position = get_position(
        request.position_id
    )

    if position is None:

        raise HTTPException(
            status_code=404,
            detail="Position not found.",
        )

    # ---------------------------------------------
    # Save feedback
    # ---------------------------------------------

    result = update_measurement_feedback(
        measurement_id=measurement_id,
        position_id=request.position_id,
        correct=request.correct,
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Measurement not found.",
        )

    # ---------------------------------------------
    # IMPORTANT:
    #
    # Rebuild the in-memory fingerprint model
    # immediately after new feedback is saved.
    #
    # This means the next recording can use the
    # newly confirmed example without restarting
    # the server.
    # ---------------------------------------------

    predictor.refresh_learning()

    return {
        "success": True,
        "measurement": result,
    }


# =========================================================
# DISCARD
# =========================================================


@router.delete(
    "/measurements/{measurement_id}",
)
async def discard_measurement(
    measurement_id: int,
):

    existing_measurement = get_measurement(
        measurement_id
    )

    if existing_measurement is None:

        raise HTTPException(
            status_code=404,
            detail="Measurement not found.",
        )

    result = set_measurement_discarded(
        measurement_id,
        True,
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Measurement not found.",
        )

    # ---------------------------------------------
    # A discarded recording must no longer influence
    # the learned acoustic fingerprints.
    # ---------------------------------------------

    predictor.refresh_learning()

    return {
        "success": True,
        "measurement": result,
    }


# =========================================================
# RESTORE
# =========================================================


@router.post(
    "/measurements/{measurement_id}/restore",
)
async def restore_measurement(
    measurement_id: int,
):

    existing_measurement = get_measurement(
        measurement_id
    )

    if existing_measurement is None:

        raise HTTPException(
            status_code=404,
            detail="Measurement not found.",
        )

    result = set_measurement_discarded(
        measurement_id,
        False,
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Measurement not found.",
        )

    # ---------------------------------------------
    # Rebuild the learned fingerprint set.
    # ---------------------------------------------

    predictor.refresh_learning()

    return {
        "success": True,
        "measurement": result,
    }


# =========================================================
# AUDIO
# =========================================================


@router.get(
    "/measurements/{measurement_id}/audio"
)
async def measurement_audio(
    measurement_id: int,
):

    result = get_measurement(
        measurement_id
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Measurement not found.",
        )

    recording_path = (
        RECORDINGS_DIR
        / result["recording_filename"]
    )

    if not recording_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Recording file not found.",
        )

    return FileResponse(
        path=recording_path,
        media_type="audio/wav",
        filename=(
            result["recording_filename"]
        ),
    )