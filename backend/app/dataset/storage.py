from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# =========================================================
# PATHS
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]

DATASET_DIR = (
    BACKEND_DIR
    / "data"
    / "dataset"
)

DATABASE_PATH = (
    DATASET_DIR
    / "dataset.db"
)

RECORDINGS_DIR = (
    DATASET_DIR
    / "recordings"
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def initialize_dataset_database() -> None:

    DATASET_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    RECORDINGS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                position_number INTEGER
                    NOT NULL
                    UNIQUE,

                name TEXT
                    NOT NULL,

                created_at TEXT
                    NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                sample_code TEXT
                    NOT NULL
                    UNIQUE,

                timestamp TEXT
                    NOT NULL,

                recording_filename TEXT
                    NOT NULL,

                position_id INTEGER,

                target_presence TEXT
                    NOT NULL
                    CHECK (
                        target_presence IN (
                            'yes',
                            'no',
                            'cant_say'
                        )
                    ),

                distance_cm REAL,

                remarks TEXT,

                features TEXT
                    NOT NULL,

                duration_seconds REAL
                    NOT NULL,

                sample_rate INTEGER
                    NOT NULL,

                predicted_position_id INTEGER,

                prediction_confidence REAL,

                prediction_evaluation TEXT,

                prediction_timestamp TEXT,

                FOREIGN KEY (
                    position_id
                )
                REFERENCES positions(id)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_samples_position
            ON samples(position_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_samples_target_presence
            ON samples(target_presence)
            """
        )

        connection.commit()

    finally:

        connection.close()


# =========================================================
# CONNECTION
# =========================================================

def get_connection() -> sqlite3.Connection:

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# =========================================================
# HELPERS
# =========================================================

def _utc_now() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def _row_to_position(
    row: sqlite3.Row
) -> Dict[str, Any]:

    return {
        "id": row["id"],
        "position_number":
            row["position_number"],
        "name": row["name"],
        "created_at":
            row["created_at"]
    }


def _row_to_sample(
    row: sqlite3.Row
) -> Dict[str, Any]:

    features = json.loads(
        row["features"]
    )

    return {
        "id": row["id"],

        "sample_code":
            row["sample_code"],

        "timestamp":
            row["timestamp"],

        "recording_filename":
            row["recording_filename"],

        "position_id":
            row["position_id"],

        "position_name":
            row["position_name"],

        "target_presence":
            row["target_presence"],

        "distance_cm":
            row["distance_cm"],

        "remarks":
            row["remarks"],

        "features":
            features,

        "duration_seconds":
            row["duration_seconds"],

        "sample_rate":
            row["sample_rate"],

        "predicted_position_id":
            row["predicted_position_id"],

        "predicted_position_name":
            row["predicted_position_name"],

        "prediction_confidence":
            row["prediction_confidence"],

        "prediction_evaluation":
            row["prediction_evaluation"],

        "prediction_timestamp":
            row["prediction_timestamp"]
    }


# =========================================================
# POSITIONS
# =========================================================

def get_positions() -> List[Dict[str, Any]]:

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                id,
                position_number,
                name,
                created_at
            FROM positions
            ORDER BY position_number ASC
            """
        ).fetchall()

        return [
            _row_to_position(row)
            for row in rows
        ]

    finally:

        connection.close()


def get_position(
    position_id: int
) -> Optional[Dict[str, Any]]:

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                id,
                position_number,
                name,
                created_at
            FROM positions
            WHERE id = ?
            """,
            (position_id,)
        ).fetchone()

        if row is None:
            return None

        return _row_to_position(row)

    finally:

        connection.close()


def create_position(
    name: str
) -> Dict[str, Any]:

    clean_name = name.strip()

    if not clean_name:
        raise ValueError(
            "Position name cannot be empty."
        )

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                id,
                position_number,
                name,
                created_at
            FROM positions
            WHERE LOWER(name) = LOWER(?)
            """,
            (clean_name,)
        ).fetchone()

        if row is not None:

            raise ValueError(
                "A position with this name "
                "already exists."
            )

        next_number_row = connection.execute(
            """
            SELECT
                COALESCE(
                    MAX(position_number),
                    0
                ) + 1 AS next_number
            FROM positions
            """
        ).fetchone()

        next_number = int(
            next_number_row["next_number"]
        )

        created_at = _utc_now()

        cursor = connection.execute(
            """
            INSERT INTO positions (
                position_number,
                name,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                next_number,
                clean_name,
                created_at
            )
        )

        connection.commit()

        position_id = cursor.lastrowid

        row = connection.execute(
            """
            SELECT
                id,
                position_number,
                name,
                created_at
            FROM positions
            WHERE id = ?
            """,
            (position_id,)
        ).fetchone()

        return _row_to_position(row)

    finally:

        connection.close()


# =========================================================
# SAMPLES
# =========================================================

def create_sample(
    *,
    recording_filename: str,
    position_id: Optional[int],
    target_presence: str,
    distance_cm: Optional[float],
    remarks: Optional[str],
    features: Dict[str, float],
    duration_seconds: float,
    sample_rate: int
) -> Dict[str, Any]:

    connection = get_connection()

    try:

        if position_id is not None:

            position_exists = connection.execute(
                """
                SELECT id
                FROM positions
                WHERE id = ?
                """,
                (position_id,)
            ).fetchone()

            if position_exists is None:

                raise ValueError(
                    "Selected position does not exist."
                )

        timestamp = _utc_now()

        cursor = connection.execute(
            """
            INSERT INTO samples (
                sample_code,
                timestamp,
                recording_filename,
                position_id,
                target_presence,
                distance_cm,
                remarks,
                features,
                duration_seconds,
                sample_rate
            )
            VALUES (
                '',
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                timestamp,
                recording_filename,
                position_id,
                target_presence,
                distance_cm,
                remarks,
                json.dumps(
                    features
                ),
                duration_seconds,
                sample_rate
            )
        )

        sample_id = cursor.lastrowid

        sample_code = (
            f"AL-{sample_id:04d}"
        )

        connection.execute(
            """
            UPDATE samples
            SET sample_code = ?
            WHERE id = ?
            """,
            (
                sample_code,
                sample_id
            )
        )

        connection.commit()

        return get_sample(
            sample_id
        )

    finally:

        connection.close()


def get_sample(
    sample_id: int
) -> Optional[Dict[str, Any]]:

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                s.*,
                p.name AS position_name,
                pp.name AS predicted_position_name
            FROM samples s

            LEFT JOIN positions p
                ON s.position_id = p.id

            LEFT JOIN positions pp
                ON s.predicted_position_id = pp.id

            WHERE s.id = ?
            """,
            (sample_id,)
        ).fetchone()

        if row is None:
            return None

        return _row_to_sample(row)

    finally:

        connection.close()


def get_samples() -> List[Dict[str, Any]]:

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                s.*,
                p.name AS position_name,
                pp.name AS predicted_position_name
            FROM samples s

            LEFT JOIN positions p
                ON s.position_id = p.id

            LEFT JOIN positions pp
                ON s.predicted_position_id = pp.id

            ORDER BY s.id DESC
            """
        ).fetchall()

        return [
            _row_to_sample(row)
            for row in rows
        ]

    finally:

        connection.close()


def update_sample(
    sample_id: int,
    *,
    position_id: Optional[int],
    target_presence: str,
    distance_cm: Optional[float],
    remarks: Optional[str]
) -> Optional[Dict[str, Any]]:

    connection = get_connection()

    try:

        if position_id is not None:

            position_exists = connection.execute(
                """
                SELECT id
                FROM positions
                WHERE id = ?
                """,
                (position_id,)
            ).fetchone()

            if position_exists is None:

                raise ValueError(
                    "Selected position does not exist."
                )

        existing = connection.execute(
            """
            SELECT id
            FROM samples
            WHERE id = ?
            """,
            (sample_id,)
        ).fetchone()

        if existing is None:
            return None

        connection.execute(
            """
            UPDATE samples
            SET
                position_id = ?,
                target_presence = ?,
                distance_cm = ?,
                remarks = ?,

                predicted_position_id = NULL,
                prediction_confidence = NULL,
                prediction_evaluation = NULL,
                prediction_timestamp = NULL

            WHERE id = ?
            """,
            (
                position_id,
                target_presence,
                distance_cm,
                remarks,
                sample_id
            )
        )

        connection.commit()

        return get_sample(
            sample_id
        )

    finally:

        connection.close()


def delete_sample(
    sample_id: int
) -> Optional[Dict[str, Any]]:

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                id,
                recording_filename
            FROM samples
            WHERE id = ?
            """,
            (sample_id,)
        ).fetchone()

        if row is None:
            return None

        sample = get_sample(
            sample_id
        )

        connection.execute(
            """
            DELETE FROM samples
            WHERE id = ?
            """,
            (sample_id,)
        )

        connection.commit()

        return {
            "sample": sample,
            "recording_filename":
                row["recording_filename"]
        }

    finally:

        connection.close()


# =========================================================
# TRAINING / REFERENCE DATA
# =========================================================

def get_reference_samples(
    exclude_sample_id: Optional[int] = None
) -> List[Dict[str, Any]]:

    connection = get_connection()

    try:

        if exclude_sample_id is None:

            rows = connection.execute(
                """
                SELECT
                    s.*,
                    p.name AS position_name,
                    pp.name AS predicted_position_name
                FROM samples s

                LEFT JOIN positions p
                    ON s.position_id = p.id

                LEFT JOIN positions pp
                    ON s.predicted_position_id = pp.id

                WHERE s.position_id IS NOT NULL

                ORDER BY s.id ASC
                """
            ).fetchall()

        else:

            rows = connection.execute(
                """
                SELECT
                    s.*,
                    p.name AS position_name,
                    pp.name AS predicted_position_name
                FROM samples s

                LEFT JOIN positions p
                    ON s.position_id = p.id

                LEFT JOIN positions pp
                    ON s.predicted_position_id = pp.id

                WHERE
                    s.position_id IS NOT NULL
                    AND s.id != ?

                ORDER BY s.id ASC
                """,
                (exclude_sample_id,)
            ).fetchall()

        return [
            _row_to_sample(row)
            for row in rows
        ]

    finally:

        connection.close()


# =========================================================
# PREDICTION RESULTS
# =========================================================

def save_prediction(
    sample_id: int,
    predicted_position_id: Optional[int],
    confidence: Optional[float],
    evaluation: str
) -> Optional[Dict[str, Any]]:

    connection = get_connection()

    try:

        timestamp = _utc_now()

        connection.execute(
            """
            UPDATE samples
            SET
                predicted_position_id = ?,
                prediction_confidence = ?,
                prediction_evaluation = ?,
                prediction_timestamp = ?
            WHERE id = ?
            """,
            (
                predicted_position_id,
                confidence,
                evaluation,
                timestamp,
                sample_id
            )
        )

        connection.commit()

        return get_sample(
            sample_id
        )

    finally:

        connection.close()


# =========================================================
# DATASET SUMMARY
# =========================================================

def get_summary() -> Dict[str, Any]:

    connection = get_connection()

    try:

        total_samples = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM samples
            """
        ).fetchone()["count"]

        labeled_samples = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM samples
            WHERE position_id IS NOT NULL
            """
        ).fetchone()["count"]

        evaluable_predictions = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM samples
            WHERE prediction_evaluation IN (
                'correct',
                'incorrect'
            )
            """
        ).fetchone()["count"]

        correct_predictions = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM samples
            WHERE prediction_evaluation = 'correct'
            """
        ).fetchone()["count"]

        incorrect_predictions = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM samples
            WHERE prediction_evaluation = 'incorrect'
            """
        ).fetchone()["count"]

        accuracy = None

        if evaluable_predictions > 0:

            accuracy = (
                correct_predictions
                / evaluable_predictions
            )

        position_rows = connection.execute(
            """
            SELECT
                COALESCE(
                    p.name,
                    'Unlabelled'
                ) AS name,
                COUNT(*) AS count
            FROM samples s

            LEFT JOIN positions p
                ON s.position_id = p.id

            GROUP BY
                COALESCE(
                    p.name,
                    'Unlabelled'
                )

            ORDER BY count DESC
            """
        ).fetchall()

        positions = {
            row["name"]:
                row["count"]
            for row in position_rows
        }

        target_rows = connection.execute(
            """
            SELECT
                target_presence,
                COUNT(*) AS count
            FROM samples
            GROUP BY target_presence
            """
        ).fetchall()

        target_presence = {
            row["target_presence"]:
                row["count"]
            for row in target_rows
        }

        distance_rows = connection.execute(
            """
            SELECT
                CASE
                    WHEN distance_cm IS NULL
                        THEN 'Unknown'
                    ELSE CAST(
                        distance_cm AS TEXT
                    )
                END AS distance,
                COUNT(*) AS count
            FROM samples
            GROUP BY
                CASE
                    WHEN distance_cm IS NULL
                        THEN 'Unknown'
                    ELSE CAST(
                        distance_cm AS TEXT
                    )
                END
            """
        ).fetchall()

        distances = {
            row["distance"]:
                row["count"]
            for row in distance_rows
        }

        return {
            "total_samples":
                total_samples,

            "labeled_samples":
                labeled_samples,

            "evaluable_predictions":
                evaluable_predictions,

            "correct_predictions":
                correct_predictions,

            "incorrect_predictions":
                incorrect_predictions,

            "accuracy":
                accuracy,

            "positions":
                positions,

            "target_presence":
                target_presence,

            "distances":
                distances
        }

    finally:

        connection.close()