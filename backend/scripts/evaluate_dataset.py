from __future__ import annotations

from pathlib import Path
import csv
import sys
from collections import Counter, defaultdict


# =========================================================
# PATH SETUP
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# =========================================================
# IMPORT EXISTING DATASET COMPONENTS
# =========================================================

from app.dataset.storage import get_positions, get_reference_samples
from app.dataset.predictor import DatasetPredictor


# =========================================================
# CONFIGURATION
# =========================================================

RESULTS_DIR = (
    BACKEND_DIR
    / "data"
    / "dataset"
    / "evaluation"
)

RESULTS_CSV = (
    RESULTS_DIR
    / "baseline_results.csv"
)

POSITION_NUMBERS = list(range(1, 11))


# =========================================================
# HELPERS
# =========================================================

def safe_percentage(
    numerator: int,
    denominator: int
) -> float:

    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
        * 100.0
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 80)
    print(
        "ACOUSTIC LOCALIZATION - "
        "BASELINE DATASET EVALUATION"
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

    print("\nPositions:")

    for position in positions:

        print(
            f"  ID {position['id']}: "
            f"{position['name']} "
            f"(Position "
            f"{position['position_number']})"
        )

    # -----------------------------------------------------
    # Load labelled samples
    # -----------------------------------------------------

    samples = get_reference_samples()

    print("\nDataset:")
    print(
        f"  Labelled samples: "
        f"{len(samples)}"
    )

    if not samples:

        raise RuntimeError(
            "No labelled samples found."
        )

    # -----------------------------------------------------
    # Verify distribution
    # -----------------------------------------------------

    ground_truth_counts = Counter()

    for sample in samples:

        position_id = sample.get(
            "position_id"
        )

        if position_id is None:
            continue

        position = position_by_id.get(
            position_id
        )

        if position:

            ground_truth_counts[
                position["position_number"]
            ] += 1

    print(
        "\nGround-truth distribution:"
    )

    for position_number in POSITION_NUMBERS:

        print(
            f"  Pos {position_number:2d}: "
            f"{ground_truth_counts[position_number]:2d} "
            f"samples"
        )

    # -----------------------------------------------------
    # Create predictor
    # -----------------------------------------------------

    predictor = DatasetPredictor()

    print(
        f"\nKNN configuration:"
        f"\n  K = {predictor.K}"
        f"\n  Features = "
        f"{len(predictor.FEATURE_NAMES) if hasattr(predictor, 'FEATURE_NAMES') else 12}"
        f"\n  Normalization = z-score"
        f"\n  Distance = Euclidean"
        f"\n  Voting = inverse-distance weighted"
    )

    # -----------------------------------------------------
    # Statistics
    # -----------------------------------------------------

    results = []

    correct_count = 0
    incorrect_count = 0
    skipped_count = 0

    # confusion[actual][predicted]
    confusion = defaultdict(Counter)

    # per-position statistics
    per_position = defaultdict(
        lambda: {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "confidence_sum": 0.0,
            "confidence_count": 0,
        }
    )

    total_samples = len(samples)

    # -----------------------------------------------------
    # Leave-one-out evaluation
    # -----------------------------------------------------

    print("\n")
    print("=" * 80)
    print(
        "RUNNING LEAVE-ONE-OUT PREDICTIONS"
    )
    print("=" * 80)

    print(
        "\nEach sample is excluded from "
        "its own reference set."
    )

    print()

    # -----------------------------------------------------
    # Evaluate each sample
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
                f"[{index:3d}/{total_samples}] "
                f"{sample_code:8s} | "
                f"SKIPPED - missing ground truth"
            )

            continue

        actual_number = (
            ground_truth_position[
                "position_number"
            ]
        )

        # -------------------------------------------------
        # Get reference samples
        # Exclude current sample
        # -------------------------------------------------

        reference_samples = (
            get_reference_samples(
                exclude_sample_id=sample_id
            )
        )

        if not reference_samples:

            skipped_count += 1

            print(
                f"[{index:3d}/{total_samples}] "
                f"{sample_code:8s} | "
                f"SKIPPED - no references"
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

        nearest_samples = (
            prediction.get(
                "nearest_samples",
                []
            )
        )

        # -------------------------------------------------
        # Convert predicted ID to position number
        # -------------------------------------------------

        predicted_position_number = None

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
        # Correctness
        # -------------------------------------------------

        is_correct = (
            predicted_position_id is not None
            and predicted_position_id
            == ground_truth_id
        )

        if is_correct:

            evaluation = "correct"
            correct_count += 1

        else:

            evaluation = "incorrect"
            incorrect_count += 1

        # -------------------------------------------------
        # Confusion matrix
        # -------------------------------------------------

        if predicted_position_number is not None:

            confusion[
                actual_number
            ][
                predicted_position_number
            ] += 1

        # -------------------------------------------------
        # Per-position statistics
        # -------------------------------------------------

        stats = per_position[
            actual_number
        ]

        stats["total"] += 1

        if is_correct:

            stats["correct"] += 1

        else:

            stats["incorrect"] += 1

        if confidence is not None:

            stats["confidence_sum"] += float(
                confidence
            )

            stats["confidence_count"] += 1

        # -------------------------------------------------
        # Nearest neighbors
        # -------------------------------------------------

        nearest_codes = []
        nearest_positions = []

        for neighbor in nearest_samples[:5]:

            nearest_codes.append(
                neighbor.get(
                    "sample_code",
                    ""
                )
            )

            nearest_positions.append(
                neighbor.get(
                    "position_name",
                    ""
                )
            )

        # -------------------------------------------------
        # Save result
        # -------------------------------------------------

        results.append(
            {
                "sample_id":
                    sample_id,

                "sample_code":
                    sample_code,

                "ground_truth_position_id":
                    ground_truth_id,

                "ground_truth_position":
                    ground_truth_position[
                        "name"
                    ],

                "ground_truth_position_number":
                    actual_number,

                "predicted_position_id":
                    predicted_position_id,

                "predicted_position":
                    (
                        predicted_position_name
                        if predicted_position_name
                        else "Unknown"
                    ),

                "predicted_position_number":
                    predicted_position_number,

                "confidence":
                    confidence,

                "evaluation":
                    evaluation,

                "nearest_1":
                    (
                        nearest_codes[0]
                        if len(nearest_codes) > 0
                        else ""
                    ),

                "nearest_2":
                    (
                        nearest_codes[1]
                        if len(nearest_codes) > 1
                        else ""
                    ),

                "nearest_3":
                    (
                        nearest_codes[2]
                        if len(nearest_codes) > 2
                        else ""
                    ),

                "nearest_4":
                    (
                        nearest_codes[3]
                        if len(nearest_codes) > 3
                        else ""
                    ),

                "nearest_5":
                    (
                        nearest_codes[4]
                        if len(nearest_codes) > 4
                        else ""
                    ),

                "nearest_positions":
                    " | ".join(
                        nearest_positions
                    ),
            }
        )

        # -------------------------------------------------
        # Progress
        # -------------------------------------------------

        if confidence is not None:

            confidence_text = (
                f"{float(confidence) * 100:.1f}%"
            )

        else:

            confidence_text = "N/A"

        result_text = (
            "CORRECT"
            if is_correct
            else "WRONG"
        )

        print(
            f"[{index:3d}/{total_samples}] "
            f"{sample_code:8s} | "
            f"Actual: Pos {actual_number:<2d} | "
            f"Predicted: "
            f"{predicted_position_name or 'Unknown':8s} | "
            f"Confidence: "
            f"{confidence_text:>7s} | "
            f"{result_text}"
        )

    # =====================================================
    # OVERALL RESULTS
    # =====================================================

    evaluated_count = len(results)

    accuracy = safe_percentage(
        correct_count,
        evaluated_count
    )

    # -----------------------------------------------------
    # Save CSV
    # -----------------------------------------------------

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "sample_id",
        "sample_code",
        "ground_truth_position_id",
        "ground_truth_position",
        "ground_truth_position_number",
        "predicted_position_id",
        "predicted_position",
        "predicted_position_number",
        "confidence",
        "evaluation",
        "nearest_1",
        "nearest_2",
        "nearest_3",
        "nearest_4",
        "nearest_5",
        "nearest_positions",
    ]

    with RESULTS_CSV.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            results
        )

    # =====================================================
    # PRINT OVERALL RESULTS
    # =====================================================

    print("\n")
    print("=" * 80)
    print("BASELINE RESULTS")
    print("=" * 80)

    print(
        f"\nTotal labelled samples : "
        f"{len(samples)}"
    )

    print(
        f"Evaluated samples     : "
        f"{evaluated_count}"
    )

    print(
        f"Skipped samples       : "
        f"{skipped_count}"
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
        f"\nBASELINE ACCURACY     : "
        f"{accuracy:.2f}%"
    )

    # =====================================================
    # PER-POSITION ACCURACY
    # =====================================================

    print("\n")
    print("=" * 80)
    print("PER-POSITION ACCURACY")
    print("=" * 80)

    for position_number in POSITION_NUMBERS:

        stats = per_position[
            position_number
        ]

        total = stats["total"]
        correct = stats["correct"]

        position_accuracy = safe_percentage(
            correct,
            total
        )

        if stats["confidence_count"] > 0:

            average_confidence = (
                stats["confidence_sum"]
                / stats["confidence_count"]
            )

        else:

            average_confidence = 0.0

        print(
            f"Pos {position_number:2d}: "
            f"{correct:2d}/{total:2d} correct | "
            f"Accuracy: "
            f"{position_accuracy:6.2f}% | "
            f"Avg confidence: "
            f"{average_confidence * 100:6.2f}%"
        )

    # =====================================================
    # CONFUSION MATRIX
    # =====================================================

    print("\n")
    print("=" * 80)
    print("CONFUSION MATRIX")
    print("=" * 80)

    print(
        "\nRows = Actual position"
        "\nColumns = Predicted position\n"
    )

    header = "Actual \\ Pred"

    print(
        f"{header:14s}"
        + "".join(
            f"P{position_number:>5d}"
            for position_number
            in POSITION_NUMBERS
        )
    )

    print("-" * 70)

    for actual_number in POSITION_NUMBERS:

        row = (
            f"Pos {actual_number:<8d}"
        )

        for predicted_number in POSITION_NUMBERS:

            count = confusion[
                actual_number
            ][
                predicted_number
            ]

            row += f"{count:>6d}"

        print(row)

    # =====================================================
    # MOST COMMON CONFUSIONS
    # =====================================================

    confusion_pairs = []

    for actual_number in POSITION_NUMBERS:

        for predicted_number in POSITION_NUMBERS:

            if actual_number == predicted_number:
                continue

            count = confusion[
                actual_number
            ][
                predicted_number
            ]

            if count > 0:

                confusion_pairs.append(
                    (
                        count,
                        actual_number,
                        predicted_number
                    )
                )

    confusion_pairs.sort(
        reverse=True
    )

    print("\n")
    print("=" * 80)
    print("MOST COMMON POSITION CONFUSIONS")
    print("=" * 80)

    if confusion_pairs:

        for (
            count,
            actual,
            predicted
        ) in confusion_pairs[:10]:

            print(
                f"Actual Pos {actual} "
                f"-> Predicted Pos {predicted}: "
                f"{count} samples"
            )

    else:

        print(
            "No incorrect position pairs."
        )

    # =====================================================
    # COMPLETE
    # =====================================================

    print("\n")
    print("=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)

    print(
        f"\nDetailed CSV:"
        f"\n{RESULTS_CSV}"
    )

    print(
        "\nThe evaluation did not modify "
        "the dataset database."
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()