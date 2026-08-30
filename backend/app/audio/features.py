from typing import Dict

import librosa
import numpy as np


def extract_features(
    audio: np.ndarray,
    sample_rate: int,
) -> Dict[str, float]:

    features: Dict[str, float] = {}

    if len(audio) == 0:
        raise ValueError(
            "Audio recording is empty."
        )

    # -----------------------------
    # Time-domain features
    # -----------------------------

    rms = librosa.feature.rms(
        y=audio
    )

    features["rms_mean"] = float(
        np.mean(rms)
    )

    features["rms_max"] = float(
        np.max(rms)
    )

    features["peak_amplitude"] = float(
        np.max(np.abs(audio))
    )

    # -----------------------------
    # Spectral features
    # -----------------------------

    spectral_centroid = (
        librosa.feature.spectral_centroid(
            y=audio,
            sr=sample_rate,
        )
    )

    spectral_bandwidth = (
        librosa.feature.spectral_bandwidth(
            y=audio,
            sr=sample_rate,
        )
    )

    spectral_rolloff = (
        librosa.feature.spectral_rolloff(
            y=audio,
            sr=sample_rate,
            roll_percent=0.85,
        )
    )

    spectral_flatness = (
        librosa.feature.spectral_flatness(
            y=audio,
        )
    )

    zero_crossing_rate = (
        librosa.feature.zero_crossing_rate(
            y=audio,
        )
    )

    features["spectral_centroid"] = float(
        np.mean(spectral_centroid)
    )

    features["spectral_bandwidth"] = float(
        np.mean(spectral_bandwidth)
    )

    features["spectral_rolloff"] = float(
        np.mean(spectral_rolloff)
    )

    features["spectral_flatness"] = float(
        np.mean(spectral_flatness)
    )

    features["zero_crossing_rate"] = float(
        np.mean(zero_crossing_rate)
    )

    # -----------------------------
    # Frequency-band energy
    # -----------------------------

    for start_khz in range(
        15,
        20,
    ):
        end_khz = start_khz + 1

        band_energy = frequency_band_energy(
            audio,
            sample_rate,
            start_khz * 1000,
            end_khz * 1000,
        )

        features[
            f"energy_{start_khz}_{end_khz}khz"
        ] = band_energy

    return features


def frequency_band_energy(
    audio: np.ndarray,
    sample_rate: int,
    low_frequency: float,
    high_frequency: float,
) -> float:

    spectrum = np.fft.rfft(audio)

    frequencies = np.fft.rfftfreq(
        len(audio),
        d=1 / sample_rate,
    )

    mask = (
        (frequencies >= low_frequency)
        & (
            frequencies
            < high_frequency
        )
    )

    if not np.any(mask):
        return 0.0

    magnitude = np.abs(
        spectrum[mask]
    )

    energy = np.mean(
        magnitude ** 2
    )

    return float(
        10 * np.log10(
            energy + 1e-12
        )
    )