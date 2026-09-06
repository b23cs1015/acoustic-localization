from pathlib import Path
import sqlite3


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = BACKEND_DIR / "data" / "dataset" / "dataset.db"


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

START_SAMPLE_NUMBER = 6
END_SAMPLE_NUMBER = 205
SAMPLES_PER_POSITION = 20
NUMBER_OF_POSITIONS = 10


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def sample_code(number: int) -> str:
    return f"AL-{number:04d}"


def expected_position(number: int) -> int:
    """
    Map sample numbers to positions.

    AL-0006 ... AL-0025 -> Position 1
    AL-0026 ... AL-0045 -> Position 2
    ...
    AL-0186 ... AL-0205 -> Position 10
    """
    position = ((number - START_SAMPLE_NUMBER) // SAMPLES_PER_POSITION) + 1

    if not 1 <= position <= NUMBER_OF_POSITIONS:
        raise ValueError(
            f"Sample number {number} maps outside Position 1-10."
        )

    return position


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    print("=" * 70)
    print("ACOUSTIC LOCALIZATION - DATASET POSITION LABEL MIGRATION")
    print("=" * 70)

    print(f"\nDatabase:")
    print(DATABASE_PATH)

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Dataset database not found: {DATABASE_PATH}"
        )

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()

        # -------------------------------------------------
        # 1. Verify positions
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id, position_number, name
            FROM positions
            ORDER BY position_number
            """
        )

        positions = cursor.fetchall()

        print("\nPositions found:")

        for position in positions:
            print(
                f"  ID {position['id']}: "
                f"Position {position['position_number']} "
                f"({position['name']})"
            )

        if len(positions) < NUMBER_OF_POSITIONS:
            raise RuntimeError(
                f"Expected at least {NUMBER_OF_POSITIONS} positions, "
                f"but found {len(positions)}."
            )

        # Verify IDs 1-10 correspond to position numbers 1-10.
        position_map = {
            row["position_number"]: row["id"]
            for row in positions
        }

        for position_number in range(1, NUMBER_OF_POSITIONS + 1):
            if position_number not in position_map:
                raise RuntimeError(
                    f"Position {position_number} does not exist."
                )

        # -------------------------------------------------
        # 2. Verify expected samples exist
        # -------------------------------------------------

        print("\nChecking samples...")

        expected_codes = [
            sample_code(number)
            for number in range(START_SAMPLE_NUMBER, END_SAMPLE_NUMBER + 1)
        ]

        placeholders = ",".join("?" for _ in expected_codes)

        cursor.execute(
            f"""
            SELECT id, sample_code, position_id
            FROM samples
            WHERE sample_code IN ({placeholders})
            ORDER BY sample_code
            """,
            expected_codes,
        )

        samples = cursor.fetchall()

        print(f"Expected samples : {len(expected_codes)}")
        print(f"Found samples    : {len(samples)}")

        if len(samples) != len(expected_codes):
            found_codes = {row["sample_code"] for row in samples}
            missing_codes = [
                code
                for code in expected_codes
                if code not in found_codes
            ]

            print("\nMissing samples:")

            for code in missing_codes:
                print(f"  {code}")

            raise RuntimeError(
                "Not all expected samples were found. "
                "No database changes were made."
            )

        # -------------------------------------------------
        # 3. Build migration plan
        # -------------------------------------------------

        migration = []

        for row in samples:
            code = row["sample_code"]

            number = int(code.split("-")[1])

            position_number = expected_position(number)
            position_id = position_map[position_number]

            migration.append(
                {
                    "id": row["id"],
                    "sample_code": code,
                    "position_number": position_number,
                    "position_id": position_id,
                    "old_position_id": row["position_id"],
                }
            )

        # -------------------------------------------------
        # 4. Print migration plan
        # -------------------------------------------------

        print("\nMigration plan:")
        print("-" * 70)

        for position_number in range(1, NUMBER_OF_POSITIONS + 1):
            entries = [
                item
                for item in migration
                if item["position_number"] == position_number
            ]

            print(
                f"Position {position_number:2d}: "
                f"{len(entries):2d} samples  "
                f"{entries[0]['sample_code']} -> "
                f"{entries[-1]['sample_code']}"
            )

        # -------------------------------------------------
        # 5. Safety check
        # -------------------------------------------------

        expected_total = SAMPLES_PER_POSITION * NUMBER_OF_POSITIONS

        if len(migration) != expected_total:
            raise RuntimeError(
                f"Expected {expected_total} samples, "
                f"but migration contains {len(migration)}."
            )

        for position_number in range(1, NUMBER_OF_POSITIONS + 1):
            count = sum(
                1
                for item in migration
                if item["position_number"] == position_number
            )

            if count != SAMPLES_PER_POSITION:
                raise RuntimeError(
                    f"Position {position_number} has {count} samples "
                    f"instead of {SAMPLES_PER_POSITION}."
                )

        print("-" * 70)

        print("\nEverything looks correct.")
        print("\nThe script will now update ONLY:")
        print("  samples.position_id")

        print("\nIt will NOT modify:")
        print("  - WAV recordings")
        print("  - extracted features")
        print("  - target presence")
        print("  - distance")
        print("  - remarks")
        print("  - timestamps")
        print("  - sample codes")

        # -------------------------------------------------
        # 6. Confirmation
        # -------------------------------------------------

        confirmation = input(
            "\nType LABEL to apply the position labels: "
        ).strip()

        if confirmation != "LABEL":
            print("\nCancelled. No database changes were made.")
            return

        # -------------------------------------------------
        # 7. Apply changes in a transaction
        # -------------------------------------------------

        print("\nApplying labels...")

        try:
            connection.execute("BEGIN")

            for item in migration:
                cursor.execute(
                    """
                    UPDATE samples
                    SET position_id = ?
                    WHERE id = ?
                    """,
                    (
                        item["position_id"],
                        item["id"],
                    ),
                )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        # -------------------------------------------------
        # 8. Verify final database state
        # -------------------------------------------------

        print("\nVerifying database...")

        cursor.execute(
            """
            SELECT
                p.position_number,
                p.name,
                COUNT(s.id) AS sample_count
            FROM positions p
            LEFT JOIN samples s
                ON s.position_id = p.id
            WHERE p.position_number BETWEEN 1 AND 10
            GROUP BY p.id, p.position_number, p.name
            ORDER BY p.position_number
            """
        )

        results = cursor.fetchall()

        print("\nFinal label distribution:")
        print("-" * 70)

        total = 0

        for row in results:
            count = row["sample_count"]
            total += count

            print(
                f"Position {row['position_number']:2d} "
                f"({row['name']}): "
                f"{count:2d} samples"
            )

        print("-" * 70)
        print(f"Total labeled samples: {total}")

        if total != expected_total:
            raise RuntimeError(
                f"Verification failed: expected {expected_total}, "
                f"got {total}."
            )

        print("\nSUCCESS.")
        print(
            "All 200 recordings have been assigned to "
            "Positions 1-10."
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()