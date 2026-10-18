from pathlib import Path
from datetime import datetime
import json
import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/room-mapping",
    tags=["Room Mapping"],
)


# ============================================================
# STORAGE
# ============================================================

# __file__:
# backend/app/api/room_mapping_routes.py
#
# parents[0] -> backend/app/api
# parents[1] -> backend/app
# parents[2] -> backend
BACKEND_DIR = Path(__file__).resolve().parents[2]

ROOM_MAPPING_DIR = BACKEND_DIR / "data" / "room_mappings"

ROOM_MAPPING_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get("/health")
def room_mapping_health():
    return {
        "status": "ok",
        "service": "room-mapping",
    }


# ============================================================
# UPLOAD RECORDING
# ============================================================

@router.post("/recordings")
async def upload_room_mapping_recording(
    audio: UploadFile = File(...),
    room_name: str = Form("Room 1"),
    remarks: str = Form(""),
    duration_seconds: float = Form(0.0),
    sample_rate: int = Form(48000),
    start_frequency: float = Form(15000.0),
    end_frequency: float = Form(20000.0),
    chirp_duration: float = Form(1.0),
):
    """
    Upload one continuous room-mapping recording.

    The WAV file contains the microphone recording while
    the smartphone continuously plays the acoustic chirp.
    """

    # --------------------------------------------------------
    # Validate filename
    # --------------------------------------------------------

    if not audio.filename:
        raise HTTPException(
            status_code=400,
            detail="No audio filename provided.",
        )

    # --------------------------------------------------------
    # Validate content type
    # --------------------------------------------------------

    allowed_types = {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "application/octet-stream",
    }

    if audio.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio type: {audio.content_type}",
        )

    # --------------------------------------------------------
    # Read uploaded audio
    # --------------------------------------------------------

    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded audio file is empty.",
        )

    # --------------------------------------------------------
    # File size limit
    # --------------------------------------------------------

    max_size = 100 * 1024 * 1024

    if len(audio_bytes) > max_size:
        raise HTTPException(
            status_code=413,
            detail="Audio file is too large. Maximum size is 100 MB.",
        )

    # --------------------------------------------------------
    # Generate unique recording ID
    # --------------------------------------------------------

    mapping_id = (
        datetime.now().strftime("%Y%m%d_%H%M%S")
        + "_"
        + uuid.uuid4().hex[:8]
    )

    audio_filename = f"{mapping_id}.wav"
    metadata_filename = f"{mapping_id}.json"

    audio_path = ROOM_MAPPING_DIR / audio_filename
    metadata_path = ROOM_MAPPING_DIR / metadata_filename

    # --------------------------------------------------------
    # Save WAV
    # --------------------------------------------------------

    audio_path.write_bytes(audio_bytes)

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    created_at = datetime.now().isoformat()

    metadata = {
        "mapping_id": mapping_id,
        "room_name": room_name,
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

    # --------------------------------------------------------
    # Save metadata JSON
    # --------------------------------------------------------

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "success": True,

        "mapping_id": mapping_id,

        "filename": audio_filename,

        "duration_seconds": duration_seconds,

        "sample_rate": sample_rate,

        "created_at": created_at,

        "download_url": (
            f"/api/room-mapping/"
            f"recordings/{mapping_id}/audio"
        ),

        "metadata_url": (
            f"/api/room-mapping/"
            f"recordings/{mapping_id}/metadata"
        ),
    }


# ============================================================
# DOWNLOAD AUDIO
# ============================================================

@router.get("/recordings/{mapping_id}/audio")
def download_room_mapping_audio(
    mapping_id: str,
):
    """
    Download a previously uploaded WAV recording.
    """

    audio_path = (
        ROOM_MAPPING_DIR
        / f"{mapping_id}.wav"
    )

    if not audio_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Room mapping recording not found.",
        )

    return FileResponse(
        path=audio_path,
        media_type="audio/wav",
        filename=audio_path.name,
    )


# ============================================================
# GET METADATA
# ============================================================

@router.get("/recordings/{mapping_id}/metadata")
def get_room_mapping_metadata(
    mapping_id: str,
):
    """
    Return metadata for a room mapping recording.
    """

    metadata_path = (
        ROOM_MAPPING_DIR
        / f"{mapping_id}.json"
    )

    if not metadata_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Room mapping metadata not found.",
        )

    try:
        metadata = json.loads(
            metadata_path.read_text(
                encoding="utf-8"
            )
        )

        return metadata

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Stored metadata is invalid.",
        )