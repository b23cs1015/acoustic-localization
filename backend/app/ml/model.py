from typing import Dict, List, Optional, Tuple

import numpy as np


class AcousticModel:

    """
    Acoustic localization model.

    Current behaviour:

    1. If feedback data exists, use the
       feedback-trained nearest-neighbour model.

    2. Otherwise use the original baseline.

    This keeps the prototype functional before
    the final trained research model is integrated.
    """

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

            features = item["features"]

            vector = self._features_to_vector(
                features
            )

            self.training_features.append(
                vector
            )

            self.training_labels.append(
                f"Position {item['position_number']}"
            )

    def _features_to_vector(
        self,
        features: Dict[str, float],
    ) -> np.ndarray:

        """
        Keep feature ordering deterministic.
        """

        return np.array(
            [
                features.get(
                    "rms_mean",
                    0.0,
                ),

                features.get(
                    "rms_max",
                    0.0,
                ),

                features.get(
                    "peak_amplitude",
                    0.0,
                ),

                features.get(
                    "spectral_centroid",
                    0.0,
                ),

                features.get(
                    "spectral_bandwidth",
                    0.0,
                ),

                features.get(
                    "spectral_rolloff",
                    0.0,
                ),

                features.get(
                    "spectral_flatness",
                    0.0,
                ),

                features.get(
                    "zero_crossing_rate",
                    0.0,
                ),

                features.get(
                    "energy_15_16khz",
                    0.0,
                ),

                features.get(
                    "energy_16_17khz",
                    0.0,
                ),

                features.get(
                    "energy_17_18khz",
                    0.0,
                ),

                features.get(
                    "energy_18_19khz",
                    0.0,
                ),

                features.get(
                    "energy_19_20khz",
                    0.0,
                ),
            ],
            dtype=np.float32,
        )

    # =====================================================
    # PREDICTION
    # =====================================================

    def predict(
        self,
        features: Dict[str, float],
    ) -> Tuple[str, Optional[float]]:

        # ---------------------------------------------
        # Feedback-trained prediction
        # ---------------------------------------------

        if self.training_features:

            return self._feedback_prediction(
                features
            )

        # ---------------------------------------------
        # Original baseline
        # ---------------------------------------------

        return self._baseline_prediction(
            features
        )

    def _feedback_prediction(
        self,
        features: Dict[str, float],
    ) -> Tuple[str, Optional[float]]:

        current = self._features_to_vector(
            features
        )

        training = np.array(
            self.training_features,
            dtype=np.float32,
        )

        # Normalize each feature dimension so
        # large-valued features do not dominate.
        mean = np.mean(
            training,
            axis=0,
        )

        std = np.std(
            training,
            axis=0,
        )

        std[std < 1e-8] = 1.0

        normalized_training = (
            training - mean
        ) / std

        normalized_current = (
            current - mean
        ) / std

        distances = np.linalg.norm(
            normalized_training
            - normalized_current,
            axis=1,
        )

        nearest_index = int(
            np.argmin(distances)
        )

        prediction = self.training_labels[
            nearest_index
        ]

        # Convert distance into a simple
        # prototype confidence estimate.
        nearest_distance = float(
            distances[nearest_index]
        )

        confidence = float(
            1.0
            / (
                1.0
                + nearest_distance
            )
        )

        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        return prediction, confidence

    # =====================================================
    # ORIGINAL BASELINE
    # =====================================================

    def _baseline_prediction(
        self,
        features: Dict[str, float],
    ) -> Tuple[str, Optional[float]]:

        energy = np.mean(
            [
                value
                for key, value in features.items()
                if key.startswith(
                    "energy_"
                )
            ]
        )

        if energy > -20:

            prediction = "Position 1"

        elif energy > -35:

            prediction = "Position 2"

        else:

            prediction = "Position 3"

        return prediction, None