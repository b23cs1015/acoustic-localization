from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np


# =========================================================
# EXISTING DATASET FEATURE SET
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

    The original 12-feature baseline is preserved.

    A separate STFT/PSD prediction method is also provided
    for the next experimental stage.
    """

    K = 5

    # -----------------------------------------------------
    # Existing handcrafted feature vector
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
    # Generic vector conversion
    # -----------------------------------------------------

    @staticmethod
    def _fingerprint_to_vector(
        fingerprint: Any
    ) -> Optional[np.ndarray]:

        if fingerprint is None:
            return None

        try:

            vector = np.asarray(
                fingerprint,
                dtype=np.float64
            ).reshape(-1)

        except (
            TypeError,
            ValueError
        ):

            return None

        if vector.size == 0:
            return None

        vector = np.nan_to_num(
            vector,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        return vector

    # -----------------------------------------------------
    # Generic weighted KNN prediction
    # -----------------------------------------------------

    def _predict_from_vectors(
        self,
        sample: Dict[str, Any],
        current_vector: np.ndarray,
        reference_samples: List[
            Dict[str, Any]
        ],
        reference_vectors: List[np.ndarray],
    ) -> Dict[str, Any]:

        if not reference_samples:
            return self._not_evaluable_result()

        if not reference_vectors:
            return self._not_evaluable_result()

        if len(reference_samples) != len(
            reference_vectors
        ):
            raise ValueError(
                "Reference sample/vector count mismatch."
            )

        # -------------------------------------------------
        # Keep only compatible vectors
        # -------------------------------------------------

        valid_samples = []
        valid_vectors = []

        for reference, vector in zip(
            reference_samples,
            reference_vectors
        ):

            if reference.get(
                "position_id"
            ) is None:
                continue

            if vector is None:
                continue

            if vector.size != current_vector.size:
                continue

            if not np.all(
                np.isfinite(vector)
            ):
                continue

            valid_samples.append(
                reference
            )

            valid_vectors.append(
                vector
            )

        if not valid_vectors:
            return self._not_evaluable_result()

        # -------------------------------------------------
        # Build matrix
        # -------------------------------------------------

        matrix = np.vstack(
            valid_vectors
        )

        # -------------------------------------------------
        # Feature normalization
        # -------------------------------------------------
        #
        # Statistics are calculated only from the reference
        # samples, never from the test sample.
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

            weight = (
                1.0
                / (distance + 1e-6)
            )

            votes[position_id] = (
                votes.get(
                    position_id,
                    0.0
                )
                + weight
            )

        if not votes:
            return self._not_evaluable_result()

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
            / (
                1.0
                + nearest_distance
            )
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

    # -----------------------------------------------------
    # Existing 12-feature baseline
    # -----------------------------------------------------

    def predict(
        self,
        sample: Dict[str, Any],
        reference_samples: List[
            Dict[str, Any]
        ]
    ) -> Dict[str, Any]:

        if not reference_samples:
            return self._not_evaluable_result()

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
            return self._not_evaluable_result()

        return self._predict_from_vectors(
            sample=sample,
            current_vector=current_vector,
            reference_samples=valid_samples,
            reference_vectors=training_vectors,
        )

    # -----------------------------------------------------
    # STFT / PSD predictor
    # -----------------------------------------------------

    def predict_stft_psd(
        self,
        sample: Dict[str, Any],
        reference_samples: List[
            Dict[str, Any]
        ]
    ) -> Dict[str, Any]:

        """
        Predict using STFT/PSD fingerprints.

        The caller must provide the fingerprint under:

            sample["_stft_psd_fingerprint"]

        and:

            reference["_stft_psd_fingerprint"]

        This keeps the raw WAV processing outside the predictor
        and allows the same predictor to be used for experiments.
        """

        current_vector = (
            self._fingerprint_to_vector(
                sample.get(
                    "_stft_psd_fingerprint"
                )
            )
        )

        if current_vector is None:
            return self._not_evaluable_result()

        valid_samples = []
        reference_vectors = []

        for reference in reference_samples:

            if reference.get(
                "position_id"
            ) is None:
                continue

            vector = (
                self._fingerprint_to_vector(
                    reference.get(
                        "_stft_psd_fingerprint"
                    )
                )
            )

            if vector is None:
                continue

            if vector.size != current_vector.size:
                continue

            valid_samples.append(
                reference
            )

            reference_vectors.append(
                vector
            )

        if not reference_vectors:
            return self._not_evaluable_result()

        return self._predict_from_vectors(
            sample=sample,
            current_vector=current_vector,
            reference_samples=valid_samples,
            reference_vectors=reference_vectors,
        )

    # -----------------------------------------------------
    # Not evaluable helper
    # -----------------------------------------------------

    @staticmethod
    def _not_evaluable_result() -> Dict[str, Any]:

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