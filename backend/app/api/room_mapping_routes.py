from pathlib import Path
from datetime import datetime
from typing import Optional

import json
import re
import shutil
import uuid

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
)

from fastapi.responses import FileResponse


router = APIRouter(
    prefix="/api/room-mapping",
    tags=["Room Mapping"],
)


# =====================================================
# STORAGE CONFIGURATION
# =====================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]

ROOM_MAPPING_DIR = (
    BACKEND_DIR / "data" / "room_mappings"
).resolve()

ROOM_MAPPING_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def safe_name(value: str) -> str:
    value = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        value.strip(),
    ).strip("_")

    if not value:
        raise HTTPException(
            status_code=400,
            detail="Invalid identifier.",
        )

    return value[:80]


def get_experiment_dir(
    experiment_number: str
) -> Path:
    return (
        ROOM_MAPPING_DIR / safe_name(experiment_number)
    ).resolve()


def ensure_inside_root(path: Path) -> Path:
    resolved = path.resolve()

    try:
        resolved.relative_to(ROOM_MAPPING_DIR)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid storage path.",
        )

    return resolved


def read_json(path: Path):
    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read metadata: {exc}",
        )


def write_json(
    path: Path,
    data: dict,
):
    path.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def get_recording_metadata():
    records = []

    for metadata_path in ROOM_MAPPING_DIR.rglob("*.json"):
        if metadata_path.name == "experiment.json":
            continue

        try:
            data = json.loads(
                metadata_path.read_text(encoding="utf-8")
            )

            if "mapping_id" in data:
                records.append(data)

        except Exception:
            continue

    return sorted(
        records,
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )


def get_recording_paths(mapping_id: str):
    if not re.fullmatch(
        r"[a-fA-F0-9]{32}",
        mapping_id,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid recording ID.",
        )

    for metadata_path in ROOM_MAPPING_DIR.rglob(
        f"{mapping_id}.json"
    ):
        if metadata_path.name == "experiment.json":
            continue

        audio_path = metadata_path.with_suffix(".wav")

        if audio_path.exists():
            return audio_path, metadata_path

    raise HTTPException(
        status_code=404,
        detail="Recording not found.",
    )


# =====================================================
# HEALTH
# =====================================================

@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "room-mapping",
    }


# =====================================================
# CREATE EXPERIMENT
# =====================================================

@router.post("/experiments")
def create_experiment(
    experiment_number: str = Form(...),
    experiment_title: str = Form(...),
    description: str = Form(""),
    room_name: str = Form("Room 1"),
):
    number = safe_name(experiment_number)
    title = experiment_title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Experiment title is required.",
        )

    experiment_dir = get_experiment_dir(number)

    if experiment_dir.exists():
        raise HTTPException(
            status_code=409,
            detail=(
                "Experiment already exists. "
                "Select Continue Existing Experiment."
            ),
        )

    experiment_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    metadata = {
        "experiment_number": number,
        "experiment_title": title,
        "description": description,
        "room_name": room_name,
        "created_at": datetime.now().isoformat(),
    }

    write_json(
        experiment_dir / "experiment.json",
        metadata,
    )

    return {
        "success": True,
        **metadata,
        "total_recordings": 0,
        "total_positions": 0,
        "positions": [],
    }


# =====================================================
# LIST EXPERIMENTS
# =====================================================

@router.get("/experiments")
def list_experiments():
    experiments = []
    all_records = get_recording_metadata()

    for experiment_dir in ROOM_MAPPING_DIR.iterdir():
        if not experiment_dir.is_dir():
            continue

        metadata_path = experiment_dir / "experiment.json"

        if not metadata_path.exists():
            continue

        try:
            metadata = read_json(metadata_path)

            number = metadata.get("experiment_number")

            records = [
                record
                for record in all_records
                if record.get("experiment_number") == number
            ]

            positions = sorted({
                record.get("position_id")
                for record in records
                if record.get("position_id")
            })

            experiments.append({
                **metadata,
                "total_recordings": len(records),
                "total_positions": len(positions),
                "positions": positions,
            })

        except Exception:
            continue

    return sorted(
        experiments,
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )


# =====================================================
# DELETE COMPLETE EXPERIMENT
# =====================================================

@router.delete("/experiments/{experiment_number}")
def remove_experiment(experiment_number: str):
    """
    Permanently remove one experiment folder and all
    associated batches, WAV recordings and JSON metadata.
    """

    experiment_dir = ensure_inside_root(
        get_experiment_dir(experiment_number)
    )

    if (
        not experiment_dir.exists()
        or not experiment_dir.is_dir()
    ):
        raise HTTPException(
            status_code=404,
            detail="Experiment not found.",
        )

    metadata_path = experiment_dir / "experiment.json"

    if not metadata_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Experiment metadata not found.",
        )

    records = [
        record
        for record in get_recording_metadata()
        if record.get("experiment_number")
        == safe_name(experiment_number)
    ]

    batch_dirs = {
        str(path.parent)
        for path in experiment_dir.rglob("*.json")
        if path.name != "experiment.json"
    }

    shutil.rmtree(experiment_dir)

    return {
        "success": True,
        "deleted_experiment": safe_name(experiment_number),
        "deleted_batches": len(batch_dirs),
        "deleted_recordings": len(records),
    }


# =====================================================
# DELETE INDIVIDUAL BATCH
# =====================================================

@router.delete(
    "/experiments/{experiment_number}/batches/{batch_id}"
)
def remove_batch(
    experiment_number: str,
    batch_id: str,
):
    """
    Remove a batch ID from every position folder
    inside the specified experiment only.
    """

    experiment_dir = ensure_inside_root(
        get_experiment_dir(experiment_number)
    )

    if (
        not experiment_dir.exists()
        or not (experiment_dir / "experiment.json").exists()
    ):
        raise HTTPException(
            status_code=404,
            detail="Experiment not found.",
        )

    batch = safe_name(batch_id)
    candidates = []

    for position_dir in experiment_dir.iterdir():
        if not position_dir.is_dir():
            continue

        candidate = ensure_inside_root(
            position_dir / batch
        )

        if candidate.exists() and candidate.is_dir():
            candidates.append(candidate)

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="Batch not found in this experiment.",
        )

    deleted_recordings = 0

    for batch_dir in candidates:
        deleted_recordings += sum(
            1
            for path in batch_dir.glob("*.json")
            if path.name != "experiment.json"
        )

        shutil.rmtree(batch_dir)

        # Remove the position folder if it is now empty.
        parent = batch_dir.parent

        if (
            parent != experiment_dir
            and parent.exists()
            and not any(parent.iterdir())
        ):
            parent.rmdir()

    return {
        "success": True,
        "deleted_batch": batch,
        "deleted_recordings": deleted_recordings,
    }


# =====================================================
# UPLOAD RECORDING
# =====================================================

@router.post("/recordings")
async def upload_recording(
    audio: UploadFile = File(...),

    experiment_number: str = Form(...),
    experiment_title: str = Form(...),

    room_name: str = Form("Room 1"),
    position_id: str = Form(...),

    distance_cm: Optional[float] = Form(None),
    x_cm: Optional[float] = Form(None),
    y_cm: Optional[float] = Form(None),
    phone_height_cm: Optional[float] = Form(None),

    remarks: str = Form(""),

    duration_seconds: float = Form(0.0),
    sample_rate: int = Form(48000),

    start_frequency: float = Form(15000.0),
    end_frequency: float = Form(20000.0),
    chirp_duration: float = Form(1.0),

    batch_id: str = Form(""),

    recording_number: Optional[int] = Form(None),
    total_recordings: Optional[int] = Form(None),
):
    # -------------------------------------------------
    # VALIDATION
    # -------------------------------------------------

    if not audio.filename:
        raise HTTPException(
            status_code=400,
            detail="Audio filename missing.",
        )

    if not position_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Position ID is required.",
        )

    if duration_seconds < 0 or sample_rate <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid duration or sample rate.",
        )

    for label, value in (
        ("Distance", distance_cm),
        ("X coordinate", x_cm),
        ("Y coordinate", y_cm),
        ("Phone height", phone_height_cm),
    ):
        if value is not None and value < 0:
            raise HTTPException(
                status_code=400,
                detail=f"{label} cannot be negative.",
            )

    # -------------------------------------------------
    # READ AUDIO
    # -------------------------------------------------

    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded audio is empty.",
        )

    if len(audio_bytes) > 100 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Maximum recording size is 100 MB.",
        )

    # -------------------------------------------------
    # EXPERIMENT VALIDATION
    # -------------------------------------------------

    number = safe_name(experiment_number)

    experiment_dir = ensure_inside_root(
        get_experiment_dir(number)
    )

    experiment_metadata_path = (
        experiment_dir / "experiment.json"
    )

    if not experiment_metadata_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Experiment does not exist. Create it first.",
        )

    experiment_metadata = read_json(
        experiment_metadata_path
    )

    if (
        experiment_metadata.get("experiment_title")
        != experiment_title
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Experiment title does not match "
                "the selected experiment."
            ),
        )

    # -------------------------------------------------
    # CREATE POSITION AND BATCH DIRECTORIES
    # -------------------------------------------------

    position = safe_name(position_id)

    batch = safe_name(
        batch_id
        if batch_id
        else f"MANUAL_{uuid.uuid4().hex[:12]}"
    )

    batch_dir = ensure_inside_root(
        experiment_dir / position / batch
    )

    batch_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------
    # GENERATE UNIQUE FILE NAMES
    # -------------------------------------------------

    mapping_id = uuid.uuid4().hex

    audio_filename = f"{mapping_id}.wav"
    metadata_filename = f"{mapping_id}.json"

    audio_path = batch_dir / audio_filename
    metadata_path = batch_dir / metadata_filename

    # -------------------------------------------------
    # SAVE WAV
    # -------------------------------------------------

    audio_path.write_bytes(audio_bytes)

    # -------------------------------------------------
    # CREATE METADATA
    # -------------------------------------------------

    created_at = datetime.now().isoformat()

    metadata = {
        "mapping_id": mapping_id,

        "experiment_number": number,
        "experiment_title": experiment_title,

        "room_name": room_name,

        "position_id": position,

        "distance_cm": distance_cm,

        "x_cm": x_cm,
        "y_cm": y_cm,

        "phone_height_cm": phone_height_cm,

        "batch_id": batch,

        "recording_number": recording_number,
        "total_recordings": total_recordings,

        "remarks": remarks,

        "original_filename": audio.filename,
        "saved_filename": audio_filename,

        "duration_seconds": duration_seconds,
        "sample_rate": sample_rate,

        "start_frequency": start_frequency,
        "end_frequency": end_frequency,
        "chirp_duration": chirp_duration,

        "file_size_bytes": len(audio_bytes),

        "created_at": created_at,
    }

    write_json(
        metadata_path,
        metadata,
    )

    # -------------------------------------------------
    # RESPONSE
    # -------------------------------------------------

    return {
        "success": True,

        "mapping_id": mapping_id,
        "filename": audio_filename,

        "duration_seconds": duration_seconds,
        "sample_rate": sample_rate,

        "created_at": created_at,

        "experiment_number": number,
        "position_id": position,

        "download_url": (
            f"/api/room-mapping/"
            f"recordings/{mapping_id}/audio"
        ),

        "metadata_url": (
            f"/api/room-mapping/"
            f"recordings/{mapping_id}/metadata"
        ),
    }


# =====================================================
# RECORDING HISTORY
# =====================================================

@router.get("/recordings")
def list_recordings(
    experiment_number: Optional[str] = None,
    position_id: Optional[str] = None,
):
    records = get_recording_metadata()

    if experiment_number:
        number = safe_name(experiment_number)

        records = [
            record
            for record in records
            if record.get("experiment_number") == number
        ]

    if position_id:
        position = safe_name(position_id)

        records = [
            record
            for record in records
            if record.get("position_id") == position
        ]

    return {
        "total": len(records),
        "recordings": records,
    }


# =====================================================
# DOWNLOAD AUDIO
# =====================================================

@router.get("/recordings/{mapping_id}/audio")
def download_audio(mapping_id: str):
    audio_path, _ = get_recording_paths(mapping_id)

    return FileResponse(
        path=audio_path,
        media_type="audio/wav",
        filename=audio_path.name,
    )


# =====================================================
# DOWNLOAD METADATA
# =====================================================

@router.get("/recordings/{mapping_id}/metadata")
def download_metadata(mapping_id: str):
    _, metadata_path = get_recording_paths(mapping_id)

    return FileResponse(
        path=metadata_path,
        media_type="application/json",
        filename=metadata_path.name,
    )