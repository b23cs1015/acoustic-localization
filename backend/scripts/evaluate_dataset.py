from __future__ import annotations

from pathlib import Path
import csv
import sys
from collections import Counter, defaultdict

import librosa
import numpy as np


# =========================================================
# PATH SETUP
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIR)
    )


# =========================================================
# IMPORT DATASET COMPONENTS
# =========================================================

from app.dataset.storage import (
    get_positions,
    get_reference_samples,
    RECORDINGS_DIR,
)

from app.dataset.predictor import (
    DatasetPredictor,
)

from app.audio.features import (
    extract_stft_psd_fingerprint,
    get_stft_psd_fingerprint_metadata,
)


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
    / "stft_psd_results.csv"
)

POSITION_NUMBERS = list(
    range(1, 11)
)


# =========================================================
# HELPERS
# =========================================================

def safe_percentage(
    numerator: int,
    denominator: int,
) -> float:

    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
        * 100.0
    )


def load_sample_audio(
    sample: dict,
) -> tuple[np.ndarray, int]:

    recording_filename = (
        sample.get(
            "recording_filename"
        )
    )

    if not recording_filename:
        raise FileNotFoundError(
            "Sample does not contain "
            "a recording filename."
        )

    recording_path = (
        RECORDINGS_DIR
        / recording_filename
    )

    if not recording_path.exists():
        raise FileNotFoundError(
            f"Recording not found: "
            f"{recording_path}"
        )

    audio, sample_rate = librosa.load(
        str(recording_path),
        sr=None,
        mono=True,
    )

    if audio.size == 0:
        raise ValueError(
            f"Recording is empty: "
            f"{recording_path}"
        )

    return (
        audio.astype(
            np.float64
        ),
        int(sample_rate),
    )


def build_fingerprint(
    sample: dict,
) -> np.ndarray:

    audio, sample_rate = (
        load_sample_audio(
            sample
        )
    )

    fingerprint = (
        extract_stft_psd_fingerprint(
            audio=audio,
            sample_rate=sample_rate,
        )
    )

    return fingerprint


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 80)
    print(
        "ACOUSTIC LOCALIZATION - "
        "STFT/PSD FINGERPRINT EVALUATION"
    )
    print("=" * 80)

    print(
        "\nThis experiment uses the existing "
        "raw WAV recordings."
    )

    print(
        "The original baseline results "
        "are not modified."
    )

    # -----------------------------------------------------
    # STFT / PSD configuration
    # -----------------------------------------------------

    metadata = (
        get_stft_psd_fingerprint_metadata(
            sample_rate=48000
        )
    )

    print("\nSTFT/PSD configuration:")
    print(
        f"  FFT size             : "
        f"{int(metadata['n_fft'])}"
    )

    print(
        f"  Hop length           : "
        f"{int(metadata['hop_length'])}"
    )

    print(
        f"  Frequency resolution : "
        f"{metadata['frequency_resolution_hz']:.3f} Hz"
    )

    print(
        f"  Fingerprint band     : "
        f"{metadata['fingerprint_low_hz']:.0f}"
        f"-"
        f"{metadata['fingerprint_high_hz']:.0f} Hz"
    )

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

    if not samples:
        raise RuntimeError(
            "No labelled samples found."
        )

    print("\nDataset:")
    print(
        f"  Labelled samples: "
        f"{len(samples)}"
    )

    # -----------------------------------------------------
    # Ground-truth distribution
    # -----------------------------------------------------

    ground_truth_counts = Counter()

    for sample in samples:

        position_id = sample.get(
            "position_id"
        )

        position = position_by_id.get(
            position_id
        )

        if position is not None:

            ground_truth_counts[
                position[
                    "position_number"
                ]
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
    # Create all fingerprints once
    # -----------------------------------------------------
    #
    # The raw recordings are independent of the prediction
    # reference set, so the fingerprint itself can be
    # calculated once per sample.
    #
    # Normalization is still calculated inside the predictor
    # using only the leave-one-out reference fingerprints.
    # -----------------------------------------------------

    print("\n")
    print("=" * 80)
    print(
        "BUILDING STFT/PSD FINGERPRINTS"
    )
    print("=" * 80)

    fingerprint_by_sample_id = {}

    fingerprint_failures = []

    total_samples = len(samples)

    for index, sample in enumerate(
        samples,
        start=1
    ):

        sample_code = sample[
            "sample_code"
        ]

        try:

            fingerprint = (
                build_fingerprint(
                    sample
                )
            )

            fingerprint_by_sample_id[
                sample["id"]
            ] = fingerprint

            print(
                f"[{index:3d}/{total_samples}] "
                f"{sample_code:8s} | "
                f"Fingerprint dimensions: "
                f"{fingerprint.size}"
            )

        except Exception as error:

            fingerprint_failures.append(
                {
                    "sample_id":
                        sample["id"],

                    "sample_code":
                        sample_code,

                    "error":
                        str(error),
                }
            )

            print(
                f"[{index:3d}/{total_samples}] "
                f"{sample_code:8s} | "
                f"FAILED: {error}"
            )

    print(
        "\nSuccessfully generated "
        f"{len(fingerprint_by_sample_id)} "
        f"fingerprints."
    )

    if fingerprint_failures:

        print(
            f"Fingerprint failures: "
            f"{len(fingerprint_failures)}"
        )

    if not fingerprint_by_sample_id:

        raise RuntimeError(
            "No STFT/PSD fingerprints "
            "could be generated."
        )

    # -----------------------------------------------------
    # Predictor
    # -----------------------------------------------------

    predictor = DatasetPredictor()

    print(
        f"\nWKNN configuration:"
        f"\n  K = {predictor.K}"
        f"\n  Distance = Euclidean"
        f"\n  Normalization = z-score"
        f"\n  Voting = inverse-distance weighted"
    )

    # -----------------------------------------------------
    # Statistics
    # -----------------------------------------------------

    results = []

    correct_count = 0
    incorrect_count = 0
    skipped_count = 0

    confusion = defaultdict(
        Counter
    )

    per_position = defaultdict(
        lambda: {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "confidence_sum": 0.0,
            "confidence_count": 0,
        }
    )

    correct_confidences = []
    incorrect_confidences = []

    # -----------------------------------------------------
    # Leave-one-out evaluation
    # -----------------------------------------------------

    print("\n")
    print("=" * 80)
    print(
        "RUNNING STFT/PSD LEAVE-ONE-OUT "
        "EVALUATION"
    )
    print("=" * 80)

    print(
        "\nEach test sample is excluded "
        "from its own reference set."
    )

    print(
        "Normalization statistics are "
        "calculated only from the reference samples."
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

        sample_code = sample[
            "sample_code"
        ]

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

        # -------------------------------------------------
        # Missing fingerprint
        # -------------------------------------------------

        current_fingerprint = (
            fingerprint_by_sample_id.get(
                sample_id
            )
        )

        if current_fingerprint is None:

            skipped_count += 1

            print(
                f"[{index:3d}/{total_samples}] "
                f"{sample_code:8s} | "
                f"SKIPPED - fingerprint unavailable"
            )

            continue

        actual_number = (
            ground_truth_position[
                "position_number"
            ]
        )

        # -------------------------------------------------
        # Reference samples
        # -------------------------------------------------

        reference_samples = (
            get_reference_samples(
                exclude_sample_id=sample_id
            )
        )

        reference_with_fingerprints = []

        for reference in reference_samples:

            reference_fingerprint = (
                fingerprint_by_sample_id.get(
                    reference["id"]
                )
            )

            if reference_fingerprint is None:
                continue

            reference_copy = dict(
                reference
            )

            reference_copy[
                "_stft_psd_fingerprint"
            ] = reference_fingerprint

            reference_with_fingerprints.append(
                reference_copy
            )

        # -------------------------------------------------
        # Build test sample copy
        # -------------------------------------------------

        test_sample = dict(
            sample
        )

        test_sample[
            "_stft_psd_fingerprint"
        ] = current_fingerprint

        if not reference_with_fingerprints:

            skipped_count += 1

            print(
                f"[{index:3d}/{total_samples}] "
                f"{sample_code:8s} | "
                f"SKIPPED - no reference fingerprints"
            )

            continue

        # -------------------------------------------------
        # Prediction
        # -------------------------------------------------

        prediction = (
            predictor.predict_stft_psd(
                test_sample,
                reference_with_fingerprints,
            )
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
        # Predicted position number
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

            confidence_value = float(
                confidence
            )

            stats[
                "confidence_sum"
            ] += confidence_value

            stats[
                "confidence_count"
            ] += 1

            if is_correct:

                correct_confidences.append(
                    confidence_value
                )

            else:

                incorrect_confidences.append(
                    confidence_value
                )

        # -------------------------------------------------
        # Nearest-neighbour information
        # -------------------------------------------------

        nearest_codes = []
        nearest_positions = []
        nearest_distances = []

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

            nearest_distances.append(
                neighbor.get(
                    "distance",
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

                "nearest_distances":
                    " | ".join(
                        str(value)
                        for value
                        in nearest_distances
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

    evaluated_count = len(
        results
    )

    accuracy = safe_percentage(
        correct_count,
        evaluated_count
    )

    # -----------------------------------------------------
    # Average confidence
    # -----------------------------------------------------

    if correct_confidences:

        average_correct_confidence = (
            float(
                np.mean(
                    correct_confidences
                )
            )
        )

    else:

        average_correct_confidence = 0.0

    if incorrect_confidences:

        average_incorrect_confidence = (
            float(
                np.mean(
                    incorrect_confidences
                )
            )
        )

    else:

        average_incorrect_confidence = 0.0

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
        "nearest_distances",
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
    # PRINT RESULTS
    # =====================================================

    print("\n")
    print("=" * 80)
    print(
        "STFT/PSD RESULTS"
    )
    print("=" * 80)

    print(
        f"\nTotal labelled samples : "
        f"{len(samples)}"
    )

    print(
        f"Fingerprints generated : "
        f"{len(fingerprint_by_sample_id)}"
    )

    print(
        f"Evaluated samples      : "
        f"{evaluated_count}"
    )

    print(
        f"Skipped samples        : "
        f"{skipped_count}"
    )

    print(
        f"Correct predictions    : "
        f"{correct_count}"
    )

    print(
        f"Incorrect predictions  : "
        f"{incorrect_count}"
    )

    print(
        f"\nSTFT/PSD ACCURACY      : "
        f"{accuracy:.2f}%"
    )

    print(
        f"\nAverage confidence "
        f"(correct)   : "
        f"{average_correct_confidence * 100:.2f}%"
    )

    print(
        f"Average confidence "
        f"(incorrect) : "
        f"{average_incorrect_confidence * 100:.2f}%"
    )

    # =====================================================
    # PER-POSITION ACCURACY
    # =====================================================

    print("\n")
    print("=" * 80)
    print(
        "STFT/PSD PER-POSITION ACCURACY"
    )
    print("=" * 80)

    for position_number in POSITION_NUMBERS:

        stats = per_position[
            position_number
        ]

        total = stats["total"]

        correct = stats["correct"]

        position_accuracy = (
            safe_percentage(
                correct,
                total
            )
        )

        if stats[
            "confidence_count"
        ] > 0:

            average_confidence = (
                stats[
                    "confidence_sum"
                ]
                / stats[
                    "confidence_count"
                ]
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
    print(
        "STFT/PSD CONFUSION MATRIX"
    )
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

    print(
        "-" * 70
    )

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

            if (
                actual_number
                == predicted_number
            ):
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
                        predicted_number,
                    )
                )

    confusion_pairs.sort(
        reverse=True
    )

    print("\n")
    print("=" * 80)
    print(
        "STFT/PSD MOST COMMON CONFUSIONS"
    )
    print("=" * 80)

    if confusion_pairs:

        for (
            count,
            actual,
            predicted,
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
    # BASELINE COMPARISON
    # =====================================================

    baseline_accuracy = 82.50

    improvement = (
        accuracy
        - baseline_accuracy
    )

    print("\n")
    print("=" * 80)
    print(
        "COMPARISON WITH CURRENT BASELINE"
    )
    print("=" * 80)

    print(
        f"\nCurrent baseline "
        f"(12 handcrafted features): "
        f"{baseline_accuracy:.2f}%"
    )

    print(
        f"STFT/PSD fingerprint: "
        f"{accuracy:.2f}%"
    )

    print(
        f"Difference: "
        f"{improvement:+.2f} percentage points"
    )

    # =====================================================
    # COMPLETE
    # =====================================================

    print("\n")
    print("=" * 80)
    print(
        "STFT/PSD EVALUATION COMPLETE"
    )
    print("=" * 80)

    print(
        f"\nDetailed CSV:"
        f"\n{RESULTS_CSV}"
    )

    print(
        "\nThe dataset database was not modified."
    )

    print(
        "The existing baseline results were not modified."
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()