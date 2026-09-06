from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


# =========================================================
# DATASET FEATURE SET
# =========================================================

FEATURE_NAMES = [
    "rms_dB",
    "peak_dB",
    "spectral_centroid_Hz",
    "spectral_bandwidth_Hz",
    "spectral_rolloff_Hz",
    "spectral_flatness",
    "zero_crossing_rate",
    "15_16kHz_dB",
    "16_17kHz_dB",
    "17_18kHz_dB",
    "18_19kHz_dB",
    "19_20kHz_dB"
]


# =========================================================
# DATASET KNN PREDICTOR
# =========================================================

class DatasetPredictor:

    """
    Dataset-specific acoustic fingerprint predictor.

    This intentionally remains a simple KNN-style baseline.

    The predictor compares the acoustic fingerprint of one
    dataset sample against other labelled samples and uses
    distance-weighted voting to estimate the position.
    """

    K = 5

    # -----------------------------------------------------
    # Feature vector
    # -----------------------------------------------------

    @staticmethod
    def _features_to_vector(
        features: Dict[str, Any]
    ) -> np.ndarray:

        values = []

        for feature_name in FEATURE_NAMES:

            value = features.get(
                feature_name,
                0.0
            )

            try:

                numeric_value = float(
                    value
                )

                if not np.isfinite(
                    numeric_value
                ):

                    numeric_value = 0.0

            except (
                TypeError,
                ValueError
            ):

                numeric_value = 0.0

            values.append(
                numeric_value
            )

        return np.asarray(
            values,
            dtype=np.float64
        )

    # -----------------------------------------------------
    # Predict
    # -----------------------------------------------------

    def predict(
        self,
        sample: Dict[str, Any],
        reference_samples: List[
            Dict[str, Any]
        ]
    ) -> Dict[str, Any]:

        if not reference_samples:

            return {
                "predicted_position_id":
                    None,

                "predicted_position_name":
                    None,

                "confidence":
                    None,

                "evaluation":
                    "not_evaluable",

                "nearest_samples":
                    []
            }

        current_vector = (
            self._features_to_vector(
                sample["features"]
            )
        )

        training_vectors = []

        valid_samples = []

        for reference in reference_samples:

            if reference.get(
                "position_id"
            ) is None:

                continue

            vector = (
                self._features_to_vector(
                    reference["features"]
                )
            )

            training_vectors.append(
                vector
            )

            valid_samples.append(
                reference
            )

        if not training_vectors:

            return {
                "predicted_position_id":
                    None,

                "predicted_position_name":
                    None,

                "confidence":
                    None,

                "evaluation":
                    "not_evaluable",

                "nearest_samples":
                    []
            }

        matrix = np.vstack(
            training_vectors
        )

        # -------------------------------------------------
        # Feature normalization
        # -------------------------------------------------

        means = np.mean(
            matrix,
            axis=0
        )

        standard_deviations = np.std(
            matrix,
            axis=0
        )

        standard_deviations[
            standard_deviations < 1e-12
        ] = 1.0

        normalized_matrix = (
            matrix - means
        ) / standard_deviations

        normalized_current = (
            current_vector - means
        ) / standard_deviations

        # -------------------------------------------------
        # Euclidean distance
        # -------------------------------------------------

        differences = (
            normalized_matrix
            - normalized_current
        )

        distances = np.linalg.norm(
            differences,
            axis=1
        )

        order = np.argsort(
            distances
        )

        k = min(
            self.K,
            len(order)
        )

        nearest_indices = (
            order[:k]
        )

        # -------------------------------------------------
        # Weighted voting
        # -------------------------------------------------

        votes: Dict[int, float] = {}

        for index in nearest_indices:

            reference = valid_samples[
                index
            ]

            position_id = int(
                reference["position_id"]
            )

            distance = float(
                distances[index]
            )

            weight = 1.0 / (
                distance + 1e-6
            )

            votes[position_id] = (
                votes.get(
                    position_id,
                    0.0
                )
                + weight
            )

        if not votes:

            return {
                "predicted_position_id":
                    None,

                "predicted_position_name":
                    None,

                "confidence":
                    None,

                "evaluation":
                    "not_evaluable",

                "nearest_samples":
                    []
            }

        predicted_position_id = max(
            votes,
            key=votes.get
        )

        total_vote_weight = sum(
            votes.values()
        )

        winning_vote_weight = votes[
            predicted_position_id
        ]

        voting_confidence = (
            winning_vote_weight
            / total_vote_weight
            if total_vote_weight > 0
            else 0.0
        )

        nearest_distance = float(
            distances[
                nearest_indices[0]
            ]
        )

        distance_confidence = (
            1.0
            / (1.0 + nearest_distance)
        )

        confidence = (
            0.7 * voting_confidence
            + 0.3 * distance_confidence
        )

        confidence = float(
            np.clip(
                confidence,
                0.0,
                1.0
            )
        )

        # -------------------------------------------------
        # Nearest samples
        # -------------------------------------------------

        nearest_samples = []

        for index in nearest_indices:

            reference = valid_samples[
                index
            ]

            nearest_samples.append(
                {
                    "sample_id":
                        int(
                            reference["id"]
                        ),

                    "sample_code":
                        reference[
                            "sample_code"
                        ],

                    "position_name":
                        reference.get(
                            "position_name"
                        ),

                    "distance":
                        float(
                            distances[index]
                        )
                }
            )

        # -------------------------------------------------
        # Predicted position name
        # -------------------------------------------------

        predicted_position_name = None

        for reference in valid_samples:

            if (
                int(
                    reference["position_id"]
                )
                == predicted_position_id
            ):

                predicted_position_name = (
                    reference.get(
                        "position_name"
                    )
                )

                break

        # -------------------------------------------------
        # Ground truth evaluation
        # -------------------------------------------------

        actual_position_id = sample.get(
            "position_id"
        )

        if actual_position_id is None:

            evaluation = (
                "not_evaluable"
            )

        elif (
            int(actual_position_id)
            == predicted_position_id
        ):

            evaluation = "correct"

        else:

            evaluation = "incorrect"

        return {
            "predicted_position_id":
                predicted_position_id,

            "predicted_position_name":
                predicted_position_name,

            "confidence":
                confidence,

            "evaluation":
                evaluation,

            "nearest_samples":
                nearest_samples
        }