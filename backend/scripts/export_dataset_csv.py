from __future__ import annotations

from pathlib import Path
import csv
import sys


# =========================================================
# PATH SETUP
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# =========================================================
# IMPORT EXISTING DATASET COMPONENTS
# =========================================================

from app.dataset.storage import (  # noqa: E402
    get_positions,
    get_reference_samples,
)

from app.dataset.predictor import DatasetPredictor  # noqa: E402

from app.dataset.predictor import FEATURE_NAMES  # noqa: E402


# =========================================================
# OUTPUT DIRECTORY
# =========================================================

EXPORT_DIR = (
    BACKEND_DIR
    / "data"
    / "dataset"
    / "exports"
)

FEATURES_CSV = (
    EXPORT_DIR
    / "dataset_features.csv"
)

PREDICTIONS_CSV = (
    EXPORT_DIR
    / "dataset_predictions.csv"
)


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 80)
    print(
        "ACOUSTIC LOCALIZATION - "
        "DATASET CSV EXPORT"
    )
    print("=" * 80)

    # -----------------------------------------------------
    # Load positions
    # -----------------------------------------------------

    positions = get_positions()

    if not positions:
        raise RuntimeError(
            "No dataset positions found."
        )

    position_by_id = {
        position["id"]: position
        for position in positions
    }

    # -----------------------------------------------------
    # Load labelled samples
    # -----------------------------------------------------

    samples = get_reference_samples()

    if not samples:
        raise RuntimeError(
            "No labelled dataset samples found."
        )

    print(
        f"\nFound {len(samples)} labelled samples."
    )

    print(
        f"Using {len(FEATURE_NAMES)} acoustic features."
    )

    # -----------------------------------------------------
    # Create output directory
    # -----------------------------------------------------

    EXPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # =====================================================
    # EXPORT 1: FEATURE VECTORS
    # =====================================================

    print("\n")
    print("-" * 80)
    print("EXPORTING FEATURE VECTORS")
    print("-" * 80)

    feature_fieldnames = [
        "sample_id",
        "sample_code",
        "timestamp",
        "recording_filename",
        "position_id",
        "position_name",
        "position_number",
        "target_presence",
        "distance_cm",
        "remarks",
        "duration_seconds",
        "sample_rate",
    ] + FEATURE_NAMES

    feature_rows = []

    for sample in samples:

        position_id = sample.get(
            "position_id"
        )

        position = position_by_id.get(
            position_id
        )

        row = {
            "sample_id":
                sample["id"],

            "sample_code":
                sample["sample_code"],

            "timestamp":
                sample["timestamp"],

            "recording_filename":
                sample["recording_filename"],

            "position_id":
                position_id,

            "position_name":
                (
                    position["name"]
                    if position
                    else ""
                ),

            "position_number":
                (
                    position["position_number"]
                    if position
                    else ""
                ),

            "target_presence":
                sample.get(
                    "target_presence",
                    ""
                ),

            "distance_cm":
                sample.get(
                    "distance_cm",
                    ""
                ),

            "remarks":
                sample.get(
                    "remarks",
                    ""
                ),

            "duration_seconds":
                sample.get(
                    "duration_seconds",
                    ""
                ),

            "sample_rate":
                sample.get(
                    "sample_rate",
                    ""
                ),
        }

        # ---------------------------------------------
        # Add all 12 feature values
        # ---------------------------------------------

        features = sample.get(
            "features",
            {}
        )

        for feature_name in FEATURE_NAMES:

            value = features.get(
                feature_name,
                0.0
            )

            row[feature_name] = value

        feature_rows.append(row)

    # -----------------------------------------------------
    # Write feature CSV
    # -----------------------------------------------------

    with FEATURES_CSV.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=feature_fieldnames
        )

        writer.writeheader()

        writer.writerows(
            feature_rows
        )

    print(
        f"\nFeature CSV created:"
        f"\n{FEATURES_CSV}"
    )

    print(
        f"Rows exported: "
        f"{len(feature_rows)}"
    )

    # =====================================================
    # EXPORT 2: PREDICTION RESULTS
    # =====================================================

    print("\n")
    print("-" * 80)
    print("EXPORTING PREDICTIONS")
    print("-" * 80)

    print(
        "\nUsing leave-one-out evaluation:"
    )

    print(
        "Each recording is excluded from "
        "its own reference set."
    )

    predictor = DatasetPredictor()

    prediction_fieldnames = [
        "sample_id",
        "sample_code",
        "timestamp",
        "ground_truth_position_id",
        "ground_truth_position",
        "ground_truth_position_number",
        "predicted_position_id",
        "predicted_position",
        "predicted_position_number",
        "confidence",
        "evaluation",
        "nearest_1_sample",
        "nearest_1_position",
        "nearest_1_distance",
        "nearest_2_sample",
        "nearest_2_position",
        "nearest_2_distance",
        "nearest_3_sample",
        "nearest_3_position",
        "nearest_3_distance",
        "nearest_4_sample",
        "nearest_4_position",
        "nearest_4_distance",
        "nearest_5_sample",
        "nearest_5_position",
        "nearest_5_distance",
    ]

    prediction_rows = []

    correct_count = 0
    incorrect_count = 0
    skipped_count = 0

    # -----------------------------------------------------
    # Predict every sample
    # -----------------------------------------------------

    for index, sample in enumerate(
        samples,
        start=1
    ):

        sample_id = sample["id"]
        sample_code = sample["sample_code"]

        ground_truth_id = sample.get(
            "position_id"
        )

        ground_truth_position = (
            position_by_id.get(
                ground_truth_id
            )
        )

        # -------------------------------------------------
        # Missing ground truth
        # -------------------------------------------------

        if ground_truth_position is None:

            skipped_count += 1

            print(
                f"[{index:3d}/{len(samples)}] "
                f"{sample_code} -> SKIPPED"
            )

            continue

        # -------------------------------------------------
        # Leave current sample out
        # -------------------------------------------------

        reference_samples = (
            get_reference_samples(
                exclude_sample_id=sample_id
            )
        )

        if not reference_samples:

            skipped_count += 1

            print(
                f"[{index:3d}/{len(samples)}] "
                f"{sample_code} -> SKIPPED"
            )

            continue

        # -------------------------------------------------
        # Existing predictor
        # -------------------------------------------------

        prediction = predictor.predict(
            sample,
            reference_samples
        )

        predicted_position_id = (
            prediction.get(
                "predicted_position_id"
            )
        )

        predicted_position_name = (
            prediction.get(
                "predicted_position_name"
            )
        )

        confidence = prediction.get(
            "confidence"
        )

        evaluation = prediction.get(
            "evaluation",
            "not_evaluable"
        )

        nearest_samples = prediction.get(
            "nearest_samples",
            []
        )

        # -------------------------------------------------
        # Predicted position number
        # -------------------------------------------------

        predicted_position_number = ""

        if predicted_position_id is not None:

            predicted_position = (
                position_by_id.get(
                    predicted_position_id
                )
            )

            if predicted_position:

                predicted_position_number = (
                    predicted_position[
                        "position_number"
                    ]
                )

        # -------------------------------------------------
        # Statistics
        # -------------------------------------------------

        if evaluation == "correct":

            correct_count += 1

        elif evaluation == "incorrect":

            incorrect_count += 1

        # -------------------------------------------------
        # Create row
        # -------------------------------------------------

        row = {
            "sample_id":
                sample_id,

            "sample_code":
                sample_code,

            "timestamp":
                sample["timestamp"],

            "ground_truth_position_id":
                ground_truth_id,

            "ground_truth_position":
                ground_truth_position[
                    "name"
                ],

            "ground_truth_position_number":
                ground_truth_position[
                    "position_number"
                ],

            "predicted_position_id":
                predicted_position_id
                if predicted_position_id is not None
                else "",

            "predicted_position":
                (
                    predicted_position_name
                    if predicted_position_name
                    else "Unknown"
                ),

            "predicted_position_number":
                predicted_position_number,

            "confidence":
                confidence
                if confidence is not None
                else "",

            "evaluation":
                evaluation,
        }

        # -------------------------------------------------
        # Add top 5 nearest neighbors
        # -------------------------------------------------

        for neighbor_number in range(1, 6):

            prefix = (
                f"nearest_{neighbor_number}"
            )

            if (
                len(nearest_samples)
                >= neighbor_number
            ):

                neighbor = (
                    nearest_samples[
                        neighbor_number - 1
                    ]
                )

                row[
                    f"{prefix}_sample"
                ] = neighbor.get(
                    "sample_code",
                    ""
                )

                row[
                    f"{prefix}_position"
                ] = neighbor.get(
                    "position_name",
                    ""
                )

                row[
                    f"{prefix}_distance"
                ] = neighbor.get(
                    "distance",
                    ""
                )

            else:

                row[
                    f"{prefix}_sample"
                ] = ""

                row[
                    f"{prefix}_position"
                ] = ""

                row[
                    f"{prefix}_distance"
                ] = ""

        prediction_rows.append(row)

        # -------------------------------------------------
        # Progress
        # -------------------------------------------------

        confidence_text = (
            f"{float(confidence) * 100:.1f}%"
            if confidence is not None
            else "N/A"
        )

        print(
            f"[{index:3d}/{len(samples)}] "
            f"{sample_code:8s} | "
            f"Actual: "
            f"{ground_truth_position['name']:6s} | "
            f"Predicted: "
            f"{predicted_position_name or 'Unknown':8s} | "
            f"Confidence: "
            f"{confidence_text:>7s} | "
            f"{evaluation.upper()}"
        )

    # -----------------------------------------------------
    # Write prediction CSV
    # -----------------------------------------------------

    with PREDICTIONS_CSV.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=prediction_fieldnames
        )

        writer.writeheader()

        writer.writerows(
            prediction_rows
        )

    # =====================================================
    # FINAL SUMMARY
    # =====================================================

    evaluated_count = (
        correct_count
        + incorrect_count
    )

    accuracy = (
        correct_count
        / evaluated_count
        * 100.0
        if evaluated_count > 0
        else 0.0
    )

    print("\n")
    print("=" * 80)
    print("EXPORT COMPLETE")
    print("=" * 80)

    print(
        f"\nFeature rows exported : "
        f"{len(feature_rows)}"
    )

    print(
        f"Prediction rows       : "
        f"{len(prediction_rows)}"
    )

    print(
        f"Correct predictions   : "
        f"{correct_count}"
    )

    print(
        f"Incorrect predictions : "
        f"{incorrect_count}"
    )

    print(
        f"Skipped samples       : "
        f"{skipped_count}"
    )

    print(
        f"Baseline accuracy     : "
        f"{accuracy:.2f}%"
    )

    print(
        f"\nFeature CSV:"
        f"\n{FEATURES_CSV}"
    )

    print(
        f"\nPrediction CSV:"
        f"\n{PREDICTIONS_CSV}"
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()