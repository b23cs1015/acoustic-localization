from pathlib import Path
import sqlite3
from typing import Optional


# ============================================================
# PATHS
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATASET_DIR = BACKEND_DIR / "data" / "dataset"
DATABASE_PATH = DATASET_DIR / "dataset.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# DATABASE INITIALIZATION / MIGRATION
# ============================================================

def initialize_experiment_database():
    """
    Initialize the experiment architecture.

    Existing samples and positions are assigned to EXP-001.

    This function is intentionally idempotent:
    running it multiple times should not create duplicate
    experiments or repeatedly modify the schema.
    """

    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_connection()

    try:
        # ----------------------------------------------------
        # Make sure foreign-key enforcement is disabled during
        # the schema migration.
        # ----------------------------------------------------
        conn.execute("PRAGMA foreign_keys = OFF")

        # ----------------------------------------------------
        # 1. Create experiments table
        # ----------------------------------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ----------------------------------------------------
        # 2. Create EXP-001 if no experiment exists
        # ----------------------------------------------------
        experiment_count = conn.execute(
            "SELECT COUNT(*) FROM experiments"
        ).fetchone()[0]

        if experiment_count == 0:
            conn.execute(
                """
                INSERT INTO experiments (name, description)
                VALUES (?, ?)
                """,
                (
                    "EXP-001",
                    "Initial acoustic fingerprint localization benchmark",
                ),
            )

        # Get first experiment
        first_experiment = conn.execute(
            """
            SELECT id
            FROM experiments
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()

        experiment_id = first_experiment["id"]

        # ----------------------------------------------------
        # 3. Add experiment_id to positions if necessary
        # ----------------------------------------------------
        position_columns = conn.execute(
            "PRAGMA table_info(positions)"
        ).fetchall()

        position_column_names = {
            row["name"] for row in position_columns
        }

        if "experiment_id" not in position_column_names:

            # Check whether positions table has the old global
            # UNIQUE constraint on position_number.
            table_sql_row = conn.execute(
                """
                SELECT sql
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'positions'
                """
            ).fetchone()

            table_sql = (
                table_sql_row["sql"]
                if table_sql_row is not None
                else ""
            )

            # ------------------------------------------------
            # Rebuild positions table if old position_number
            # was globally UNIQUE.
            # ------------------------------------------------
            if "UNIQUE" in table_sql.upper():

                conn.execute(
                    """
                    CREATE TABLE positions_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        experiment_id INTEGER NOT NULL,
                        position_number INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(experiment_id, position_number),
                        UNIQUE(experiment_id, name),
                        FOREIGN KEY(experiment_id)
                            REFERENCES experiments(id)
                    )
                    """
                )

                conn.execute(
                    """
                    INSERT INTO positions_new (
                        id,
                        experiment_id,
                        position_number,
                        name,
                        created_at
                    )
                    SELECT
                        id,
                        ?,
                        position_number,
                        name,
                        created_at
                    FROM positions
                    """,
                    (experiment_id,),
                )

                conn.execute("DROP TABLE positions")

                conn.execute(
                    """
                    ALTER TABLE positions_new
                    RENAME TO positions
                    """
                )

            else:
                # ------------------------------------------------
                # If the table does not have the old UNIQUE
                # constraint, simply add the column.
                # ------------------------------------------------
                conn.execute(
                    """
                    ALTER TABLE positions
                    ADD COLUMN experiment_id INTEGER
                    """
                )

                conn.execute(
                    """
                    UPDATE positions
                    SET experiment_id = ?
                    WHERE experiment_id IS NULL
                    """,
                    (experiment_id,),
                )

        else:
            # Existing experiment_id column:
            # make sure NULL legacy rows belong to EXP-001.
            conn.execute(
                """
                UPDATE positions
                SET experiment_id = ?
                WHERE experiment_id IS NULL
                """,
                (experiment_id,),
            )

        # ----------------------------------------------------
        # 4. Add experiment_id to samples if necessary
        # ----------------------------------------------------
        sample_columns = conn.execute(
            "PRAGMA table_info(samples)"
        ).fetchall()

        sample_column_names = {
            row["name"] for row in sample_columns
        }

        if "experiment_id" not in sample_column_names:
            conn.execute(
                """
                ALTER TABLE samples
                ADD COLUMN experiment_id INTEGER
                """
            )

        # ----------------------------------------------------
        # 5. Assign all existing samples to EXP-001
        # ----------------------------------------------------
        conn.execute(
            """
            UPDATE samples
            SET experiment_id = ?
            WHERE experiment_id IS NULL
            """,
            (experiment_id,),
        )

        # ----------------------------------------------------
        # 6. Create indexes
        # ----------------------------------------------------
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_samples_experiment
            ON samples(experiment_id)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_positions_experiment
            ON positions(experiment_id)
            """
        )

        # ----------------------------------------------------
        # 7. Ensure position uniqueness per experiment
        # ----------------------------------------------------
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_positions_experiment_number
            ON positions(experiment_id, position_number)
            """
        )

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_positions_experiment_name
            ON positions(experiment_id, name)
            """
        )

        conn.commit()

    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


# ============================================================
# EXPERIMENT CRUD
# ============================================================

def list_experiments():
    """
    Return all experiments.
    """

    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                id,
                name,
                description,
                created_at
            FROM experiments
            ORDER BY id
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def get_experiment(experiment_id: int):
    """
    Return a single experiment.
    """

    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT
                id,
                name,
                description,
                created_at
            FROM experiments
            WHERE id = ?
            """,
            (experiment_id,),
        ).fetchone()

        return dict(row) if row else None

    finally:
        conn.close()


def create_experiment(
    name: str,
    description: Optional[str] = None,
):
    """
    Create a new experiment.
    """

    conn = get_connection()

    try:
        cursor = conn.execute(
            """
            INSERT INTO experiments (
                name,
                description
            )
            VALUES (?, ?)
            """,
            (
                name.strip(),
                description,
            ),
        )

        conn.commit()

        experiment_id = cursor.lastrowid

        return get_experiment(experiment_id)

    finally:
        conn.close()


# ============================================================
# EXPERIMENT STATISTICS
# ============================================================

def get_experiment_stats(experiment_id: int):
    """
    Return statistics for one experiment.
    """

    conn = get_connection()

    try:
        experiment = conn.execute(
            """
            SELECT id, name
            FROM experiments
            WHERE id = ?
            """,
            (experiment_id,),
        ).fetchone()

        if experiment is None:
            return None

        sample_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM samples
            WHERE experiment_id = ?
            """,
            (experiment_id,),
        ).fetchone()[0]

        position_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM positions
            WHERE experiment_id = ?
            """,
            (experiment_id,),
        ).fetchone()[0]

        labeled_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM samples
            WHERE experiment_id = ?
              AND position_id IS NOT NULL
            """,
            (experiment_id,),
        ).fetchone()[0]

        predicted_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM samples
            WHERE experiment_id = ?
              AND predicted_position_id IS NOT NULL
            """,
            (experiment_id,),
        ).fetchone()[0]

        return {
            "experiment_id": experiment["id"],
            "experiment_name": experiment["name"],
            "sample_count": sample_count,
            "position_count": position_count,
            "labeled_count": labeled_count,
            "predicted_count": predicted_count,
        }

    finally:
        conn.close()


# ============================================================
# EXPERIMENT POSITIONS
# ============================================================

def list_experiment_positions(experiment_id: int):
    """
    Return all positions belonging to an experiment.
    """

    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                id,
                experiment_id,
                position_number,
                name,
                created_at
            FROM positions
            WHERE experiment_id = ?
            ORDER BY position_number
            """,
            (experiment_id,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def create_experiment_position(
    experiment_id: int,
    name: str,
):
    """
    Create a position inside a specific experiment.

    Position numbers restart from 1 for every experiment.
    """

    conn = get_connection()

    try:
        experiment = conn.execute(
            """
            SELECT id
            FROM experiments
            WHERE id = ?
            """,
            (experiment_id,),
        ).fetchone()

        if experiment is None:
            raise ValueError(
                f"Experiment {experiment_id} does not exist."
            )

        name = name.strip()

        if not name:
            raise ValueError("Position name cannot be empty.")

        # Check duplicate name within this experiment.
        existing_name = conn.execute(
            """
            SELECT id
            FROM positions
            WHERE experiment_id = ?
              AND name = ?
            """,
            (
                experiment_id,
                name,
            ),
        ).fetchone()

        if existing_name is not None:
            raise ValueError(
                f"Position '{name}' already exists "
                f"in experiment {experiment_id}."
            )

        # Get next position number for THIS experiment only.
        next_number = conn.execute(
            """
            SELECT COALESCE(MAX(position_number), 0) + 1
            FROM positions
            WHERE experiment_id = ?
            """,
            (experiment_id,),
        ).fetchone()[0]

        cursor = conn.execute(
            """
            INSERT INTO positions (
                experiment_id,
                position_number,
                name
            )
            VALUES (?, ?, ?)
            """,
            (
                experiment_id,
                next_number,
                name,
            ),
        )

        conn.commit()

        row = conn.execute(
            """
            SELECT
                id,
                experiment_id,
                position_number,
                name,
                created_at
            FROM positions
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

        return dict(row)

    finally:
        conn.close()