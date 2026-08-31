from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

import numpy as np

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from .storage import get_measurements


# =========================================================
# FEATURE DEFINITIONS
# =========================================================

PRIMARY_FEATURES = [
    "rms_dB",
    "peak_dB",
    "spectral_centroid_Hz",
    "spectral_bandwidth_Hz",
    "spectral_rolloff_Hz",
    "spectral_flatness",
    "zero_crossing_rate",
    "15_20kHz_dB",
    "15_20kHz_peak_dB",
]

BAND_FEATURES = [
    "15_16kHz_dB",
    "16_17kHz_dB",
    "17_18kHz_dB",
    "18_19kHz_dB",
    "19_20kHz_dB",
]

ALL_ANALYSIS_FEATURES = (
    PRIMARY_FEATURES
    + BAND_FEATURES
)


# =========================================================
# HELPERS
# =========================================================


def _numeric(value: Any) -> float | None:

    if value is None:
        return None

    try:

        number = float(value)

        if not np.isfinite(number):
            return None

        return number

    except (TypeError, ValueError):

        return None


def _feature_value(
    measurement: Dict[str, Any],
    name: str,
) -> float | None:

    features = measurement.get("features") or {}

    value = features.get(name)

    if value is None:

        # Compatibility with older feature names
        aliases = {
            "rms_dB": "rms_mean",
            "peak_dB": "peak_amplitude",
            "spectral_centroid_Hz":
                "spectral_centroid",
            "spectral_bandwidth_Hz":
                "spectral_bandwidth",
            "spectral_rolloff_Hz":
                "spectral_rolloff",
            "15_20kHz_dB":
                "energy_15_20khz",
            "15_20kHz_peak_dB":
                "energy_15_20khz",
        }

        alias = aliases.get(name)

        if alias:
            value = features.get(alias)

    return _numeric(value)


def _mean(values: List[float]) -> float | None:

    if not values:
        return None

    return float(np.mean(values))


def _std(values: List[float]) -> float | None:

    if not values:
        return None

    if len(values) == 1:
        return 0.0

    return float(np.std(values, ddof=1))


def _group_by(
    measurements: List[Dict[str, Any]],
    field: str,
    feature: str,
) -> List[Dict[str, Any]]:

    groups: Dict[str, List[float]] = {}

    for measurement in measurements:

        value = measurement.get(field)

        if value is None:
            continue

        feature_value = _feature_value(
            measurement,
            feature,
        )

        if feature_value is None:
            continue

        key = str(value)

        groups.setdefault(
            key,
            [],
        ).append(feature_value)

    result = []

    for key, values in groups.items():

        result.append(
            {
                "label": key,
                "count": len(values),
                "mean": _mean(values),
                "std": _std(values),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
            }
        )

    return result


# =========================================================
# SUMMARY
# =========================================================


def get_summary() -> Dict[str, Any]:

    measurements = get_measurements(
        include_discarded=True
    )

    active = [
        measurement
        for measurement in measurements
        if not measurement.get("discarded", False)
    ]

    labeled = [
        measurement
        for measurement in active
        if measurement.get("position_id") is not None
    ]

    feedback = [
        measurement
        for measurement in active
        if measurement.get("feedback_correct")
        is not None
    ]

    correct = [
        measurement
        for measurement in feedback
        if measurement.get("feedback_correct") is True
    ]

    positions = {
        measurement.get("position_id")
        for measurement in labeled
        if measurement.get("position_id") is not None
    }

    object_conditions = {
        str(measurement.get("object_between"))
        for measurement in active
        if measurement.get("object_between")
    }

    distances = {
        measurement.get("distance_cm")
        for measurement in active
        if measurement.get("distance_cm") is not None
    }

    return {
        "total_recordings": len(measurements),
        "active_recordings": len(active),
        "discarded_recordings": (
            len(measurements) - len(active)
        ),
        "labeled_recordings": len(labeled),
        "feedback_recordings": len(feedback),
        "correct_feedback": len(correct),
        "incorrect_feedback": (
            len(feedback) - len(correct)
        ),
        "feedback_accuracy": (
            len(correct) / len(feedback)
            if feedback
            else None
        ),
        "positions_used": len(positions),
        "distance_conditions": len(distances),
        "object_conditions": len(object_conditions),
    }


# =========================================================
# FEATURE DATA
# =========================================================


def get_feature_data() -> Dict[str, Any]:

    measurements = get_measurements()

    rows = []

    for measurement in measurements:

        row = {
            "id": measurement["id"],
            "recording_filename":
                measurement["recording_filename"],
            "position_id":
                measurement.get("position_id"),
            "position_number":
                measurement.get("position_number"),
            "position_name":
                measurement.get("position_name"),
            "distance_cm":
                measurement.get("distance_cm"),
            "object_between":
                measurement.get("object_between"),
            "prediction":
                measurement.get("prediction"),
            "confidence":
                measurement.get("confidence"),
        }

        for feature in ALL_ANALYSIS_FEATURES:

            row[feature] = _feature_value(
                measurement,
                feature,
            )

        rows.append(row)

    return {
        "features": ALL_ANALYSIS_FEATURES,
        "count": len(rows),
        "rows": rows,
    }


# =========================================================
# POSITION ANALYSIS
# =========================================================


def get_position_analysis() -> Dict[str, Any]:

    measurements = get_measurements()

    position_results = []

    for position_id in sorted(
        {
            m.get("position_id")
            for m in measurements
            if m.get("position_id") is not None
        }
    ):

        group = [
            m
            for m in measurements
            if m.get("position_id") == position_id
        ]

        first = group[0]

        position_results.append(
            {
                "position_id": position_id,
                "position_number":
                    first.get("position_number"),
                "position_name":
                    first.get("position_name"),
                "count": len(group),
                "rms_dB": {
                    "mean": _mean(
                        [
                            value
                            for m in group
                            if (
                                value :=
                                _feature_value(
                                    m,
                                    "rms_dB",
                                )
                            )
                            is not None
                        ]
                    ),
                    "std": _std(
                        [
                            value
                            for m in group
                            if (
                                value :=
                                _feature_value(
                                    m,
                                    "rms_dB",
                                )
                            )
                            is not None
                        ]
                    ),
                },
                "15_20kHz_dB": {
                    "mean": _mean(
                        [
                            value
                            for m in group
                            if (
                                value :=
                                _feature_value(
                                    m,
                                    "15_20kHz_dB",
                                )
                            )
                            is not None
                        ]
                    ),
                    "std": _std(
                        [
                            value
                            for m in group
                            if (
                                value :=
                                _feature_value(
                                    m,
                                    "15_20kHz_dB",
                                )
                            )
                            is not None
                        ]
                    ),
                },
            }
        )

    return {
        "positions": position_results
    }


# =========================================================
# DISTANCE ANALYSIS
# =========================================================


def get_distance_analysis() -> Dict[str, Any]:

    measurements = get_measurements()

    distances = []

    for measurement in measurements:

        distance = measurement.get(
            "distance_cm"
        )

        value = _feature_value(
            measurement,
            "15_20kHz_dB",
        )

        if distance is None or value is None:
            continue

        distances.append(
            {
                "distance_cm": float(distance),
                "value_dB": value,
                "position_name":
                    measurement.get(
                        "position_name"
                    ),
                "object_between":
                    measurement.get(
                        "object_between"
                    ),
            }
        )

    return {
        "points": distances,
        "grouped": _group_by(
            measurements,
            "distance_cm",
            "15_20kHz_dB",
        ),
    }


# =========================================================
# OBJECT ANALYSIS
# =========================================================


def get_object_analysis() -> Dict[str, Any]:

    measurements = get_measurements()

    return {
        "groups": _group_by(
            measurements,
            "object_between",
            "15_20kHz_dB",
        ),
        "points": [
            {
                "id": measurement["id"],
                "distance_cm":
                    measurement.get(
                        "distance_cm"
                    ),
                "object_between":
                    measurement.get(
                        "object_between"
                    ),
                "value_dB":
                    _feature_value(
                        measurement,
                        "15_20kHz_dB",
                    ),
            }
            for measurement in measurements
            if measurement.get(
                "object_between"
            )
            and _feature_value(
                measurement,
                "15_20kHz_dB",
            )
            is not None
        ],
    }


# =========================================================
# PCA
# =========================================================


def get_pca_analysis() -> Dict[str, Any]:

    measurements = get_measurements()

    valid_measurements = []

    matrix = []

    for measurement in measurements:

        values = []

        valid = True

        for feature in PRIMARY_FEATURES:

            value = _feature_value(
                measurement,
                feature,
            )

            if value is None:

                valid = False
                break

            values.append(value)

        if valid:

            matrix.append(values)
            valid_measurements.append(
                measurement
            )

    if len(matrix) < 5:

        return {
            "available": False,
            "reason": (
                "At least 5 complete "
                "recordings are required."
            ),
            "points": [],
        }

    X = np.asarray(
        matrix,
        dtype=float,
    )

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(X)

    pca = PCA(
        n_components=2
    )

    transformed = pca.fit_transform(
        X_scaled
    )

    points = []

    for index, measurement in enumerate(
        valid_measurements
    ):

        points.append(
            {
                "id": measurement["id"],
                "pc1": float(
                    transformed[index, 0]
                ),
                "pc2": float(
                    transformed[index, 1]
                ),
                "position_id":
                    measurement.get(
                        "position_id"
                    ),
                "position_name":
                    measurement.get(
                        "position_name"
                    ),
                "distance_cm":
                    measurement.get(
                        "distance_cm"
                    ),
                "object_between":
                    measurement.get(
                        "object_between"
                    ),
                "prediction":
                    measurement.get(
                        "prediction"
                    ),
            }
        )

    return {
        "available": True,
        "feature_count":
            len(PRIMARY_FEATURES),
        "features":
            PRIMARY_FEATURES,
        "samples": len(points),
        "pc1_variance_percent":
            float(
                pca.explained_variance_ratio_[0]
                * 100
            ),
        "pc2_variance_percent":
            float(
                pca.explained_variance_ratio_[1]
                * 100
            ),
        "points": points,
    }