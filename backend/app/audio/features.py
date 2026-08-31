from typing import Dict

import librosa
import numpy as np


def extract_features(
    audio: np.ndarray,
    sample_rate: int,
) -> Dict[str, float]:

    if len(audio) == 0:

        raise ValueError(
            "Audio recording is empty."
        )

    # =========================================================
    # REMOVE DC OFFSET
    # =========================================================

    audio = (
        audio
        - np.mean(audio)
    )

    duration = (
        len(audio)
        /
        sample_rate
    )

    # =========================================================
    # BASIC SIGNAL FEATURES
    # =========================================================

    rms = np.sqrt(
        np.mean(
            audio ** 2
        )
    )

    peak = np.max(
        np.abs(audio)
    )

    rms_db = (
        20
        *
        np.log10(
            rms + 1e-12
        )
    )

    peak_db = (
        20
        *
        np.log10(
            peak + 1e-12
        )
    )

    # =========================================================
    # STFT
    # =========================================================

    n_fft = 4096
    hop_length = 1024

    spectrum_complex = librosa.stft(
        audio,
        n_fft=n_fft,
        hop_length=hop_length,
    )

    spectrum = np.abs(
        spectrum_complex
    )

    frequencies = (
        librosa.fft_frequencies(
            sr=sample_rate,
            n_fft=n_fft,
        )
    )

    # =========================================================
    # SPECTRAL FEATURES
    # =========================================================

    centroid = (
        librosa.feature.spectral_centroid(
            S=spectrum,
            sr=sample_rate,
        )
    )

    bandwidth = (
        librosa.feature.spectral_bandwidth(
            S=spectrum,
            sr=sample_rate,
        )
    )

    rolloff = (
        librosa.feature.spectral_rolloff(
            S=spectrum,
            sr=sample_rate,
            roll_percent=0.85,
        )
    )

    flatness = (
        librosa.feature.spectral_flatness(
            S=spectrum,
        )
    )

    zcr = (
        librosa.feature.zero_crossing_rate(
            audio,
            hop_length=hop_length,
        )
    )

    # =========================================================
    # 15–20 kHz ULTRASONIC ENERGY
    # =========================================================

    ultrasonic_mask = (
        (frequencies >= 15000)
        &
        (
            frequencies
            <= min(
                20000,
                sample_rate / 2,
            )
        )
    )

    if np.any(
        ultrasonic_mask
    ):

        ultrasonic_power = np.mean(
            spectrum[
                ultrasonic_mask
            ] ** 2
        )

        ultrasonic_db = (
            10
            *
            np.log10(
                ultrasonic_power
                + 1e-12
            )
        )

        ultrasonic_peak = np.max(
            spectrum[
                ultrasonic_mask
            ] ** 2
        )

        ultrasonic_peak_db = (
            10
            *
            np.log10(
                ultrasonic_peak
                + 1e-12
            )
        )

    else:

        ultrasonic_db = np.nan
        ultrasonic_peak_db = np.nan

    # =========================================================
    # FREQUENCY FINGERPRINT
    # =========================================================

    bands = [
        (15000, 16000),
        (16000, 17000),
        (17000, 18000),
        (18000, 19000),
        (19000, 20000),
    ]

    band_features: Dict[str, float] = {}

    for low, high in bands:

        mask = (
            (frequencies >= low)
            &
            (frequencies < high)
        )

        if np.any(mask):

            power = np.mean(
                spectrum[mask] ** 2
            )

            db = (
                10
                *
                np.log10(
                    power + 1e-12
                )
            )

        else:

            db = np.nan

        band_features[
            f"{low // 1000}_{high // 1000}kHz_dB"
        ] = float(db)

    # =========================================================
    # MFCC
    # =========================================================
    #
    # Keep extracting these because they are useful for
    # future speech/environment experiments.
    #
    # The current chirp localization fingerprint does
    # not depend on them.
    # =========================================================

    mfcc = librosa.feature.mfcc(
        y=audio,
        sr=sample_rate,
        n_mfcc=13,
        n_fft=2048,
        hop_length=512,
    )

    mfcc_features: Dict[str, float] = {}

    for i in range(
        mfcc.shape[0]
    ):

        mfcc_features[
            f"MFCC_{i + 1}_mean"
        ] = float(
            np.mean(
                mfcc[i]
            )
        )

        mfcc_features[
            f"MFCC_{i + 1}_std"
        ] = float(
            np.std(
                mfcc[i]
            )
        )

    # =========================================================
    # FINAL FEATURE DICTIONARY
    # =========================================================

    result: Dict[str, float] = {

        "sample_rate":
            float(sample_rate),

        "duration_s":
            float(duration),

        "rms":
            float(rms),

        "rms_dB":
            float(rms_db),

        "peak":
            float(peak),

        "peak_dB":
            float(peak_db),

        "spectral_centroid_Hz":
            float(
                np.mean(
                    centroid
                )
            ),

        "spectral_bandwidth_Hz":
            float(
                np.mean(
                    bandwidth
                )
            ),

        "spectral_rolloff_Hz":
            float(
                np.mean(
                    rolloff
                )
            ),

        "spectral_flatness":
            float(
                np.mean(
                    flatness
                )
            ),

        "zero_crossing_rate":
            float(
                np.mean(
                    zcr
                )
            ),

        "15_20kHz_dB":
            (
                float(ultrasonic_db)
                if np.isfinite(
                    ultrasonic_db
                )
                else np.nan
            ),

        "15_20kHz_peak_dB":
            (
                float(
                    ultrasonic_peak_db
                )
                if np.isfinite(
                    ultrasonic_peak_db
                )
                else np.nan
            ),
    }

    result.update(
        band_features
    )

    result.update(
        mfcc_features
    )

    return result