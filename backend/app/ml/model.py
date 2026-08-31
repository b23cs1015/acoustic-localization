from typing import Dict, List, Optional, Tuple

import numpy as np


class AcousticModel:

    """
    Acoustic fingerprint based localization model.

    IMPORTANT DESIGN DECISION
    -------------------------

    Task 1 was an exploratory experiment.

    Its CSV data is NOT treated as the final training
    dataset because those room conditions cannot be
    reliably recreated.

    Instead, the current application learns from:

        recording
            ↓
        acoustic feature extraction
            ↓
        acoustic fingerprint
            ↓
        user-confirmed position
            ↓
        feedback training set

    Each confirmed recording becomes one example of
    the acoustic fingerprint of a position.

    Prediction uses normalized nearest-neighbour voting
    over the recordings collected by the current system.
    """

    # =====================================================
    # FEATURE DEFINITION
    # =====================================================
    #
    # These names MUST match features.py.
    #
    # They represent the acoustic fingerprint of a
    # recording.
    # =====================================================

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

        "19_20kHz_dB",

    ]

    # Number of neighbours used for voting.
    K_NEIGHBORS = 5

    def __init__(
        self,
        model_path: Optional[str] = None,
    ) -> None:

        self.model = None

        self.model_path = model_path

        self.training_features: List[
            np.ndarray
        ] = []

        self.training_labels: List[
            str
        ] = []

    # =====================================================
    # FEATURE VECTOR
    # =====================================================

    def _features_to_vector(
        self,
        features: Dict[str, float],
    ) -> np.ndarray:

        """
        Convert the acoustic feature dictionary into
        one deterministic numerical fingerprint.

        Missing or invalid values are represented as zero
        temporarily and handled again during normalization.
        """

        values = []

        for feature_name in self.FEATURE_NAMES:

            value = features.get(
                feature_name,
                0.0,
            )

            try:

                value = float(value)

            except (
                TypeError,
                ValueError,
            ):

                value = 0.0

            if not np.isfinite(value):

                value = 0.0

            values.append(value)

        return np.asarray(
            values,
            dtype=np.float32,
        )

    # =====================================================
    # FEEDBACK LEARNING
    # =====================================================

    def refresh_learning(self) -> None:

        from ..storage import (
            get_training_measurements,
        )

        training_data = (
            get_training_measurements()
        )

        self.training_features = []

        self.training_labels = []

        for item in training_data:

            features = item.get(
                "features",
                {},
            )

            vector = self._features_to_vector(
                features
            )

            self.training_features.append(
                vector
            )

            self.training_labels.append(
                f"Position {item['position_number']}"
            )

    # =====================================================
    # PREDICTION
    # =====================================================

    def predict(
        self,
        features: Dict[str, float],
    ) -> Tuple[str, Optional[float]]:

        # -------------------------------------------------
        # No confirmed training data
        # -------------------------------------------------

        if not self.training_features:

            return (
                "Insufficient training data",
                None,
            )

        return self._feedback_prediction(
            features
        )

    # =====================================================
    # FINGERPRINT DISTANCE
    # =====================================================

    def _prepare_training_matrix(
        self,
    ) -> np.ndarray:

        return np.asarray(
            self.training_features,
            dtype=np.float32,
        )

    # =====================================================
    # FEEDBACK PREDICTION
    # =====================================================

    def _feedback_prediction(
        self,
        features: Dict[str, float],
    ) -> Tuple[str, Optional[float]]:

        current = self._features_to_vector(
            features
        )

        training = (
            self._prepare_training_matrix()
        )

        # -------------------------------------------------
        # Feature-wise normalization
        # -------------------------------------------------
        #
        # Spectral centroid is measured in Hz while
        # flatness and ZCR are much smaller numbers.
        #
        # Without normalization, large numerical features
        # would dominate the distance calculation.
        # -------------------------------------------------

        mean = np.mean(
            training,
            axis=0,
        )

        std = np.std(
            training,
            axis=0,
        )

        std[
            std < 1e-8
        ] = 1.0

        normalized_training = (
            training - mean
        ) / std

        normalized_current = (
            current - mean
        ) / std

        # -------------------------------------------------
        # Euclidean fingerprint distance
        # -------------------------------------------------

        distances = np.linalg.norm(
            normalized_training
            - normalized_current,
            axis=1,
        )

        # -------------------------------------------------
        # Sort neighbours
        # -------------------------------------------------

        sorted_indices = np.argsort(
            distances
        )

        k = min(
            self.K_NEIGHBORS,
            len(sorted_indices),
        )

        neighbour_indices = (
            sorted_indices[:k]
        )

        # -------------------------------------------------
        # Weighted voting
        # -------------------------------------------------
        #
        # Closer acoustic fingerprints receive more weight.
        #
        # This is better than simply taking the single
        # closest recording when multiple recordings for
        # a position are available.
        # -------------------------------------------------

        votes: Dict[str, float] = {}

        for index in neighbour_indices:

            label = self.training_labels[
                int(index)
            ]

            distance = float(
                distances[index]
            )

            weight = 1.0 / (
                distance + 1e-6
            )

            votes[label] = (
                votes.get(
                    label,
                    0.0,
                )
                + weight
            )

        # -------------------------------------------------
        # Select winning position
        # -------------------------------------------------

        prediction = max(
            votes,
            key=votes.get,
        )

        total_vote = sum(
            votes.values()
        )

        winning_vote = votes[
            prediction
        ]

        if total_vote <= 0:

            confidence = 0.0

        else:

            confidence = (
                winning_vote
                / total_vote
            )

        # -------------------------------------------------
        # Distance-aware confidence
        # -------------------------------------------------
        #
        # Voting confidence alone can be misleading when
        # all fingerprints are far away.
        #
        # We therefore also consider the nearest acoustic
        # fingerprint distance.
        # -------------------------------------------------

        nearest_distance = float(
            distances[
                neighbour_indices[0]
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
            0.7 * confidence
            + 0.3 * distance_confidence
        )

        confidence = float(
            np.clip(
                confidence,
                0.0,
                1.0,
            )
        )

        return (
            prediction,
            confidence,
        )