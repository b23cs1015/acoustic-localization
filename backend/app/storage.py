import json
import sqlite3

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

RECORDINGS_DIR = DATA_DIR / "recordings"

DATABASE_PATH = DATA_DIR / "measurements.db"


DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RECORDINGS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# DATABASE CONNECTION
# =========================================================


def get_connection() -> sqlite3.Connection:

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# DATABASE INITIALIZATION
# =========================================================


def initialize_database() -> None:

    with get_connection() as connection:

        # =================================================
        # POSITIONS
        # =================================================

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                position_number INTEGER NOT NULL UNIQUE,

                name TEXT NOT NULL,

                created_at TEXT NOT NULL
            )
            """
        )

        # =================================================
        # MEASUREMENTS
        # =================================================

        table_exists = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'measurements'
            """
        ).fetchone()

        if table_exists is None:

            connection.execute(
                """
                CREATE TABLE measurements (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    timestamp TEXT NOT NULL,

                    recording_filename TEXT NOT NULL,

                    prediction TEXT NOT NULL,

                    confidence REAL,

                    duration_seconds REAL NOT NULL,

                    sample_rate INTEGER NOT NULL,

                    features TEXT NOT NULL,

                    position_id INTEGER,

                    object_between TEXT,

                    distance_cm REAL,

                    notes TEXT,

                    feedback_correct INTEGER,

                    feedback_timestamp TEXT,

                    discarded INTEGER NOT NULL DEFAULT 0,

                    FOREIGN KEY (position_id)
                        REFERENCES positions(id)
                )
                """
            )

        else:

            columns = connection.execute(
                """
                PRAGMA table_info(measurements)
                """
            ).fetchall()

            column_names = {
                column["name"]
                for column in columns
            }

            # ---------------------------------------------
            # FEATURES
            # ---------------------------------------------

            if "features" not in column_names:

                connection.execute(
                    """
                    ALTER TABLE measurements
                    ADD COLUMN features TEXT
                    """
                )

            # ---------------------------------------------
            # METADATA
            # ---------------------------------------------

            new_columns = {

                "position_id": "INTEGER",

                "object_between": "TEXT",

                "distance_cm": "REAL",

                "notes": "TEXT",

                "feedback_correct": "INTEGER",

                "feedback_timestamp": "TEXT",

                "discarded":
                    "INTEGER NOT NULL DEFAULT 0",
            }

            for (
                column_name,
                column_type,
            ) in new_columns.items():

                if column_name not in column_names:

                    connection.execute(
                        f"""
                        ALTER TABLE measurements
                        ADD COLUMN
                        {column_name}
                        {column_type}
                        """
                    )

            # ---------------------------------------------
            # LEGACY FEATURE COLUMNS
            # ---------------------------------------------
            #
            # These are retained only for compatibility
            # with older databases.
            #
            # They are NOT used as the new model's
            # feature definition.
            # ---------------------------------------------

            feature_columns = [

                "rms_mean",

                "rms_max",

                "peak_amplitude",

                "spectral_centroid",

                "spectral_bandwidth",

                "spectral_rolloff",

                "spectral_flatness",

                "zero_crossing_rate",

                "energy_15_16khz",

                "energy_16_17khz",

                "energy_17_18khz",

                "energy_18_19khz",

                "energy_19_20khz",
            ]

            available_features = [

                column

                for column in feature_columns

                if column in column_names
            ]

            if available_features:

                rows = connection.execute(
                    """
                    SELECT *
                    FROM measurements
                    WHERE features IS NULL
                    """
                ).fetchall()

                for row in rows:

                    features = {}

                    for feature_name in (
                        available_features
                    ):

                        value = row[
                            feature_name
                        ]

                        if value is not None:

                            features[
                                feature_name
                            ] = float(value)

                    connection.execute(
                        """
                        UPDATE measurements
                        SET features = ?
                        WHERE id = ?
                        """,
                        (
                            json.dumps(
                                features
                            ),
                            row["id"],
                        ),
                    )

            connection.execute(
                """
                UPDATE measurements
                SET features = '{}'
                WHERE features IS NULL
                """
            )

        # =================================================
        # SEED POSITION 1–25
        # =================================================

        existing_positions = connection.execute(
            """
            SELECT position_number
            FROM positions
            """
        ).fetchall()

        existing_numbers = {
            row["position_number"]
            for row in existing_positions
        }

        now = datetime.now(
            timezone.utc
        ).isoformat()

        for number in range(1, 26):

            if number not in existing_numbers:

                connection.execute(
                    """
                    INSERT INTO positions (
                        position_number,
                        name,
                        created_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        number,
                        f"Position {number}",
                        now,
                    ),
                )

        connection.commit()


# =========================================================
# POSITIONS
# =========================================================


def get_positions() -> List[Dict[str, Any]]:

    with get_connection() as connection:

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
        dict(row)
        for row in rows
    ]


def create_position(
    name: Optional[str] = None,
) -> Dict[str, Any]:

    with get_connection() as connection:

        row = connection.execute(
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
            row["next_number"]
        )

        position_name = (
            name.strip()
            if name
            and name.strip()
            else
            f"Position {next_number}"
        )

        created_at = datetime.now(
            timezone.utc
        ).isoformat()

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
                position_name,
                created_at,
            ),
        )

        connection.commit()

        return {
            "id": int(
                cursor.lastrowid
            ),
            "position_number":
                next_number,
            "name":
                position_name,
            "created_at":
                created_at,
        }


def get_position(
    position_id: int,
) -> Optional[Dict[str, Any]]:

    with get_connection() as connection:

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
            (
                position_id,
            ),
        ).fetchone()

    if row is None:

        return None

    return dict(row)


# =========================================================
# MEASUREMENTS
# =========================================================


def save_measurement(
    recording_filename: str,
    prediction: str,
    confidence: Optional[float],
    duration_seconds: float,
    sample_rate: int,
    features: Dict[str, float],
) -> int:

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    features_json = json.dumps(
        features,
        allow_nan=True,
    )

    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO measurements (
                timestamp,
                recording_filename,
                prediction,
                confidence,
                duration_seconds,
                sample_rate,
                features,
                discarded
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                timestamp,
                recording_filename,
                prediction,
                confidence,
                duration_seconds,
                sample_rate,
                features_json,
            ),
        )

        connection.commit()

        return int(
            cursor.lastrowid
        )


def _decode_measurement(
    row: sqlite3.Row,
) -> Dict[str, Any]:

    measurement = dict(row)

    raw_features = (
        measurement.get("features")
    )

    try:

        measurement["features"] = (
            json.loads(raw_features)
            if raw_features
            else {}
        )

    except (
        TypeError,
        json.JSONDecodeError,
    ):

        measurement["features"] = {}

    measurement["discarded"] = bool(
        measurement.get(
            "discarded",
            0,
        )
    )

    if (
        measurement.get(
            "feedback_correct"
        )
        is not None
    ):

        measurement[
            "feedback_correct"
        ] = bool(
            measurement[
                "feedback_correct"
            ]
        )

    return measurement


def get_measurements(
    include_discarded: bool = False,
) -> List[Dict[str, Any]]:

    query = """
        SELECT

            m.id,

            m.timestamp,

            m.recording_filename,

            m.prediction,

            m.confidence,

            m.duration_seconds,

            m.sample_rate,

            m.features,

            m.position_id,

            p.position_number,

            p.name AS position_name,

            m.object_between,

            m.distance_cm,

            m.notes,

            m.feedback_correct,

            m.feedback_timestamp,

            m.discarded

        FROM measurements m

        LEFT JOIN positions p
            ON m.position_id = p.id
    """

    if not include_discarded:

        query += """
            WHERE m.discarded = 0
        """

    query += """
        ORDER BY m.id ASC
    """

    with get_connection() as connection:

        rows = connection.execute(
            query
        ).fetchall()

    return [
        _decode_measurement(row)
        for row in rows
    ]


def get_measurement(
    measurement_id: int,
) -> Optional[Dict[str, Any]]:

    with get_connection() as connection:

        row = connection.execute(
            """
            SELECT

                m.id,

                m.timestamp,

                m.recording_filename,

                m.prediction,

                m.confidence,

                m.duration_seconds,

                m.sample_rate,

                m.features,

                m.position_id,

                p.position_number,

                p.name AS position_name,

                m.object_between,

                m.distance_cm,

                m.notes,

                m.feedback_correct,

                m.feedback_timestamp,

                m.discarded

            FROM measurements m

            LEFT JOIN positions p
                ON m.position_id = p.id

            WHERE m.id = ?
            """,
            (
                measurement_id,
            ),
        ).fetchone()

    if row is None:

        return None

    return _decode_measurement(row)


# =========================================================
# UPDATE DETAILS
# =========================================================


def update_measurement(
    measurement_id: int,
    position_id: Optional[int],
    object_between: Optional[str],
    distance_cm: Optional[float],
    notes: Optional[str],
) -> Optional[Dict[str, Any]]:

    with get_connection() as connection:

        if position_id is not None:

            position_exists = connection.execute(
                """
                SELECT id
                FROM positions
                WHERE id = ?
                """,
                (
                    position_id,
                ),
            ).fetchone()

            if position_exists is None:

                return None

        connection.execute(
            """
            UPDATE measurements

            SET
                position_id = ?,
                object_between = ?,
                distance_cm = ?,
                notes = ?

            WHERE id = ?
            """,
            (
                position_id,
                object_between,
                distance_cm,
                notes,
                measurement_id,
            ),
        )

        connection.commit()

    return get_measurement(
        measurement_id
    )


# =========================================================
# FEEDBACK
# =========================================================


def update_measurement_feedback(
    measurement_id: int,
    position_id: int,
    correct: bool,
) -> Optional[Dict[str, Any]]:

    feedback_timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    with get_connection() as connection:

        position_exists = connection.execute(
            """
            SELECT id
            FROM positions
            WHERE id = ?
            """,
            (
                position_id,
            ),
        ).fetchone()

        if position_exists is None:

            return None

        measurement_exists = connection.execute(
            """
            SELECT id
            FROM measurements
            WHERE id = ?
            """,
            (
                measurement_id,
            ),
        ).fetchone()

        if measurement_exists is None:

            return None

        connection.execute(
            """
            UPDATE measurements

            SET
                position_id = ?,
                feedback_correct = ?,
                feedback_timestamp = ?

            WHERE id = ?
            """,
            (
                position_id,
                1 if correct else 0,
                feedback_timestamp,
                measurement_id,
            ),
        )

        connection.commit()

    return get_measurement(
        measurement_id
    )


# =========================================================
# DISCARD / RESTORE
# =========================================================


def set_measurement_discarded(
    measurement_id: int,
    discarded: bool,
) -> Optional[Dict[str, Any]]:

    with get_connection() as connection:

        exists = connection.execute(
            """
            SELECT id
            FROM measurements
            WHERE id = ?
            """,
            (
                measurement_id,
            ),
        ).fetchone()

        if exists is None:

            return None

        connection.execute(
            """
            UPDATE measurements

            SET discarded = ?

            WHERE id = ?
            """,
            (
                1 if discarded else 0,
                measurement_id,
            ),
        )

        connection.commit()

    return get_measurement(
        measurement_id
    )


# =========================================================
# TRAINING DATA
# =========================================================
#
# IMPORTANT:
#
# Only recordings that have received explicit user
# feedback are returned.
#
# The old Task 1 CSV is NOT used here.
#
# The current application therefore learns from
# newly collected, user-confirmed measurements.
# =========================================================


def get_training_measurements() -> List[Dict[str, Any]]:

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT

                m.id,

                m.features,

                m.position_id,

                p.position_number

            FROM measurements m

            JOIN positions p
                ON m.position_id = p.id

            WHERE

                m.position_id IS NOT NULL

                AND m.discarded = 0

                AND m.feedback_correct IS NOT NULL

            ORDER BY m.id ASC
            """
        ).fetchall()

    result = []

    for row in rows:

        try:

            features = json.loads(
                row["features"]
            )

        except (
            TypeError,
            json.JSONDecodeError,
        ):

            continue

        if not isinstance(
            features,
            dict,
        ):

            continue

        result.append(
            {
                "id": row["id"],

                "features": features,

                "position_id":
                    row["position_id"],

                "position_number":
                    row["position_number"],
            }
        )

    return result