from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor


# =========================================================
# DISTANCE REGRESSION MODEL
# =========================================================
#
# This model predicts target distance from the same 12
# handcrafted acoustic features used by the localization
# baseline.
#
# Training data:
#   EXP-013
#   target_presence = "yes"
#   distance_cm is known
#
# EXP-013 currently contains 185 usable target-present
# recordings at:
#   5, 10, 15, 20, 25, 30 cm
#
# The model is trained on the complete labeled EXP-013 set
# for deployment/inference. The research evaluation of this
# model was performed separately using Leave-One-Position-Out
# validation.
#
# IMPORTANT:
# This is feature-based supervised regression. It is NOT
# physical time-of-flight echolocation.
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
    "19_20kHz_dB",
]


class DistancePredictor:
    """
    Extra Trees regression model for acoustic distance
    estimation.

    The model is trained lazily on first prediction so the
    application import sequence does not depend on database
    initialization order.
    """

    TRAINING_EXPERIMENT_ID = 13

    def __init__(self) -> None:

        self.model: Optional[
            ExtraTreesRegressor
        ] = None

        self.feature_medians: Optional[
            np.ndarray
        ] = None

        self.training_samples = 0

        self.min_distance_cm: Optional[float] = None
        self.max_distance_cm: Optional[float] = None

        self.training_error: Optional[str] = None

    # =====================================================
    # PATHS
    # =====================================================

    @staticmethod
    def _database_path() -> Path:

        backend_dir = (
            Path(__file__).resolve().parents[2]
        )

        return (
            backend_dir
            / "data"
            / "dataset"
            / "dataset.db"
        )

    # =====================================================
    # FEATURE VECTOR
    # =====================================================

    @staticmethod
    def _features_to_vector(
        features: Dict[str, Any],
    ) -> np.ndarray:

        values = []

        for feature_name in FEATURE_NAMES:

            value = features.get(
                feature_name,
                np.nan,
            )

            try:
                value = float(value)
            except (
                TypeError,
                ValueError,
            ):
                value = np.nan

            values.append(value)

        return np.asarray(
            values,
            dtype=np.float64,
        )

    # =====================================================
    # TRAINING DATA
    # =====================================================

    def _load_training_data(
        self,
        exclude_sample_id: Optional[int] = None,
    ):
        database_path = self._database_path()

        if not database_path.exists():

            raise FileNotFoundError(
                "Distance training database was not found: "
                f"{database_path}"
            )

        connection = sqlite3.connect(
            database_path
        )

        try:

            if exclude_sample_id is None:

                rows = connection.execute(
                    """
                    SELECT
                        id,
                        features,
                        distance_cm
                    FROM samples
                    WHERE experiment_id = ?
                      AND target_presence = 'yes'
                      AND distance_cm IS NOT NULL
                      AND features IS NOT NULL
                    ORDER BY id
                    """,
                    (
                        self.TRAINING_EXPERIMENT_ID,
                    ),
                ).fetchall()

            else:

                rows = connection.execute(
                    """
                    SELECT
                        id,
                        features,
                        distance_cm
                    FROM samples
                    WHERE experiment_id = ?
                      AND id != ?
                      AND target_presence = 'yes'
                      AND distance_cm IS NOT NULL
                      AND features IS NOT NULL
                    ORDER BY id
                    """,
                    (
                        self.TRAINING_EXPERIMENT_ID,
                        exclude_sample_id,
                    ),
                ).fetchall()

        finally:

            connection.close()

        if not rows:

            raise ValueError(
                "No labeled distance samples were found "
                f"for EXP-{self.TRAINING_EXPERIMENT_ID:03d}."
            )

        feature_rows = []
        targets = []

        for _sample_id, raw_features, distance_cm in rows:

            try:
                features = json.loads(
                    raw_features
                )
            except (
                TypeError,
                json.JSONDecodeError,
            ):
                continue

            vector = self._features_to_vector(
                features
            )

            target = float(
                distance_cm
            )

            if not np.isfinite(target):
                continue

            feature_rows.append(
                vector
            )

            targets.append(
                target
            )

        if not feature_rows:

            raise ValueError(
                "Distance training samples contained "
                "no usable feature vectors."
            )

        X = np.vstack(
            feature_rows
        )

        y = np.asarray(
            targets,
            dtype=np.float64,
        )

        return X, y

    # =====================================================
    # DATA CLEANING
    # =====================================================

    @staticmethod
    def _clean_training_matrix(
        X: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:

        X = np.asarray(
            X,
            dtype=np.float64,
        )

        # Calculate one median per feature using only
        # training samples.
        medians = np.nanmedian(
            np.where(
                np.isfinite(X),
                X,
                np.nan,
            ),
            axis=0,
        )

        # If an entire feature is invalid, fall back to zero.
        medians = np.where(
            np.isfinite(medians),
            medians,
            0.0,
        )

        cleaned = X.copy()

        invalid = ~np.isfinite(
            cleaned
        )

        if np.any(invalid):

            rows, columns = np.where(
                invalid
            )

            cleaned[
                rows,
                columns
            ] = medians[columns]

        return cleaned, medians

    # =====================================================
    # TRAIN
    # =====================================================

    def _train_model(
        self,
        exclude_sample_id: Optional[int] = None,
    ) -> tuple[
        ExtraTreesRegressor,
        np.ndarray,
        int,
        float,
        float,
    ]:
        """
        Train an Extra Trees model on the configured distance
        experiment. When exclude_sample_id is supplied, that
        sample is removed from the training set.

        The exclusion is important for sample-level evaluation:
        the sample being predicted must not also be present in
        the training set.
        """

        X, y = self._load_training_data(
            exclude_sample_id=exclude_sample_id
        )

        X, medians = self._clean_training_matrix(
            X
        )

        if len(y) < 2:
            raise ValueError(
                "At least two training samples are required "
                "for distance regression."
            )

        model = ExtraTreesRegressor(
            n_estimators=300,
            random_state=42,
            n_jobs=-1,
        )

        model.fit(
            X,
            y,
        )

        return (
            model,
            medians,
            len(y),
            float(np.min(y)),
            float(np.max(y)),
        )

    def refresh(self) -> None:
        """
        Train and cache the normal deployment model using all
        available labeled samples from EXP-013.
        """

        try:

            (
                model,
                medians,
                training_samples,
                min_distance_cm,
                max_distance_cm,
            ) = self._train_model()

            self.model = model
            self.feature_medians = medians
            self.training_samples = training_samples
            self.min_distance_cm = min_distance_cm
            self.max_distance_cm = max_distance_cm
            self.training_error = None

        except Exception as error:

            self.model = None
            self.feature_medians = None
            self.training_samples = 0
            self.min_distance_cm = None
            self.max_distance_cm = None
            self.training_error = str(error)

    # =====================================================
    # READY
    # =====================================================

    def _ensure_ready(self) -> None:

        if self.model is None:

            self.refresh()

        if self.model is None:

            raise RuntimeError(
                "Distance model is unavailable. "
                f"{self.training_error or ''}"
            )

    # =====================================================
    # PREDICT
    # =====================================================

    def predict(
        self,
        features: Dict[str, Any],
        exclude_sample_id: Optional[int] = None,
    ) -> Optional[float]:
        """
        Predict distance from an acoustic feature dictionary.

        If exclude_sample_id is provided, the model is trained
        again with that exact sample removed from EXP-013. This
        prevents training/test leakage when the API is evaluating
        a labeled sample from the distance-training experiment.

        Without an exclusion ID, the cached deployment model is
        used.
        """

        if exclude_sample_id is None:

            self._ensure_ready()

            model = self.model
            feature_medians = self.feature_medians
            min_distance_cm = self.min_distance_cm
            max_distance_cm = self.max_distance_cm

        else:

            (
                model,
                feature_medians,
                _,
                min_distance_cm,
                max_distance_cm,
            ) = self._train_model(
                exclude_sample_id=exclude_sample_id
            )

        if model is None:
            raise RuntimeError(
                "Distance model is unavailable."
            )

        if feature_medians is None:
            raise RuntimeError(
                "Distance feature statistics "
                "are not initialized."
            )

        vector = self._features_to_vector(
            features
        )

        invalid = ~np.isfinite(
            vector
        )

        if np.any(invalid):
            vector[invalid] = (
                feature_medians[invalid]
            )

        prediction = model.predict(
            vector.reshape(1, -1)
        )

        value = float(
            prediction[0]
        )

        if (
            min_distance_cm is not None
            and max_distance_cm is not None
        ):
            value = float(
                np.clip(
                    value,
                    min_distance_cm,
                    max_distance_cm,
                )
            )

        return value

    # =====================================================
    # STATUS
    # =====================================================

    def status(self) -> Dict[str, Any]:

        return {
            "available":
                self.model is not None,

            "training_experiment":
                f"EXP-{self.TRAINING_EXPERIMENT_ID:03d}",

            "training_samples":
                self.training_samples,

            "min_distance_cm":
                self.min_distance_cm,

            "max_distance_cm":
                self.max_distance_cm,

            "error":
                self.training_error,
        }
