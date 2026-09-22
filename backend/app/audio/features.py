from typing import Dict, Tuple

import librosa
import numpy as np


# =========================================================
# GENERAL AUDIO FEATURES
# =========================================================

def extract_features(
    audio: np.ndarray,
    sample_rate: int,
) -> Dict[str, float]:

    if len(audio) == 0:
        raise ValueError(
            "Audio recording is empty."
        )

    # =====================================================
    # REMOVE DC OFFSET
    # =====================================================

    audio = (
        audio
        - np.mean(audio)
    )

    duration = (
        len(audio)
        / sample_rate
    )

    # =====================================================
    # BASIC SIGNAL FEATURES
    # =====================================================

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
        * np.log10(
            rms + 1e-12
        )
    )

    peak_db = (
        20
        * np.log10(
            peak + 1e-12
        )
    )

    # =====================================================
    # STFT
    # =====================================================

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

    frequencies = librosa.fft_frequencies(
        sr=sample_rate,
        n_fft=n_fft,
    )

    # =====================================================
    # SPECTRAL FEATURES
    # =====================================================

    centroid = librosa.feature.spectral_centroid(
        S=spectrum,
        sr=sample_rate,
    )

    bandwidth = librosa.feature.spectral_bandwidth(
        S=spectrum,
        sr=sample_rate,
    )

    rolloff = librosa.feature.spectral_rolloff(
        S=spectrum,
        sr=sample_rate,
        roll_percent=0.85,
    )

    flatness = librosa.feature.spectral_flatness(
        S=spectrum,
    )

    zcr = librosa.feature.zero_crossing_rate(
        audio,
        hop_length=hop_length,
    )

    # =====================================================
    # 15–20 kHz ULTRASONIC ENERGY
    # =====================================================

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

    if np.any(ultrasonic_mask):

        ultrasonic_power = np.mean(
            spectrum[
                ultrasonic_mask
            ] ** 2
        )

        ultrasonic_db = (
            10
            * np.log10(
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
            * np.log10(
                ultrasonic_peak
                + 1e-12
            )
        )

    else:

        ultrasonic_db = np.nan
        ultrasonic_peak_db = np.nan

    # =====================================================
    # FREQUENCY FINGERPRINT
    # =====================================================

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
                * np.log10(
                    power + 1e-12
                )
            )

        else:

            db = np.nan

        band_features[
            f"{low // 1000}_{high // 1000}kHz_dB"
        ] = float(db)

    # =====================================================
    # MFCC
    # =====================================================

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

    # =====================================================
    # FINAL FEATURE DICTIONARY
    # =====================================================

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


# =========================================================
# STFT / PSD ACOUSTIC FINGERPRINT
# =========================================================
#
# This is a separate experimental representation.
#
# The existing 12-feature representation above is NOT
# replaced.
#
# The implementation follows the acoustic fingerprinting
# direction of Wang et al.:
#
#   acoustic chirp
#       ↓
#   STFT
#       ↓
#   PSD
#       ↓
#   frequency-domain fingerprint
#
# We retain the frequency region used by our current
# ultrasonic chirp (15–20 kHz).
# =========================================================

STFT_PSD_N_FFT = 4096
STFT_PSD_HOP_LENGTH = 1024

STFT_PSD_LOW_HZ = 15000.0
STFT_PSD_HIGH_HZ = 20000.0


def extract_stft_psd_fingerprint(
    audio: np.ndarray,
    sample_rate: int,
) -> np.ndarray:
    """
    Extract a fixed-size STFT/PSD acoustic fingerprint.

    The fingerprint is constructed from the average PSD
    over STFT frames in the 15–20 kHz sensing band.

    This is intentionally separate from extract_features()
    so that the original baseline remains unchanged.

    Returns
    -------
    np.ndarray
        One-dimensional PSD fingerprint.
    """

    if audio is None:
        raise ValueError(
            "Audio signal is None."
        )

    if len(audio) == 0:
        raise ValueError(
            "Audio recording is empty."
        )

    if sample_rate <= 0:
        raise ValueError(
            "Sample rate must be positive."
        )

    # -----------------------------------------------------
    # Remove DC offset
    # -----------------------------------------------------

    audio = (
        audio.astype(
            np.float64,
            copy=False
        )
        - np.mean(audio)
    )

    # -----------------------------------------------------
    # STFT
    # -----------------------------------------------------

    stft_complex = librosa.stft(
        audio,
        n_fft=STFT_PSD_N_FFT,
        hop_length=STFT_PSD_HOP_LENGTH,
        window="hann",
        center=True,
    )

    # -----------------------------------------------------
    # Power Spectral Density / power representation
    # -----------------------------------------------------

    power_spectrum = (
        np.abs(
            stft_complex
        ) ** 2
    )

    frequencies = librosa.fft_frequencies(
        sr=sample_rate,
        n_fft=STFT_PSD_N_FFT,
    )

    # -----------------------------------------------------
    # Restrict fingerprint to chirp band
    # -----------------------------------------------------

    upper_frequency = min(
        STFT_PSD_HIGH_HZ,
        sample_rate / 2.0
    )

    frequency_mask = (
        (frequencies >= STFT_PSD_LOW_HZ)
        &
        (frequencies <= upper_frequency)
    )

    if not np.any(
        frequency_mask
    ):
        raise ValueError(
            "The recording sample rate does not "
            "contain the required 15–20 kHz band."
        )

    selected_power = power_spectrum[
        frequency_mask,
        :
    ]

    # -----------------------------------------------------
    # Average PSD over time frames
    # -----------------------------------------------------
    #
    # This produces a fixed-length fingerprint
    # independent of the exact number of STFT frames.
    #
    # Each dimension corresponds to a frequency bin.
    # -----------------------------------------------------

    fingerprint = np.mean(
        selected_power,
        axis=1
    )

    # -----------------------------------------------------
    # Convert power to logarithmic scale
    # -----------------------------------------------------
    #
    # Log power reduces the extremely large dynamic range
    # typically present in acoustic spectra.
    # -----------------------------------------------------

    fingerprint_db = (
        10.0
        * np.log10(
            fingerprint
            + 1e-12
        )
    )

    # -----------------------------------------------------
    # Numerical safety
    # -----------------------------------------------------

    fingerprint_db = np.nan_to_num(
        fingerprint_db,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    return fingerprint_db.astype(
        np.float64
    )


# =========================================================
# STFT / PSD FINGERPRINT INFORMATION
# =========================================================

def get_stft_psd_fingerprint_metadata(
    sample_rate: int,
) -> Dict[str, float]:

    upper_frequency = min(
        STFT_PSD_HIGH_HZ,
        sample_rate / 2.0
    )

    frequency_bins = (
        STFT_PSD_N_FFT // 2
        + 1
    )

    frequency_resolution = (
        sample_rate
        / STFT_PSD_N_FFT
    )

    selected_bins = int(
        np.sum(
            (
                np.fft.rfftfreq(
                    STFT_PSD_N_FFT,
                    d=1.0 / sample_rate
                )
                >= STFT_PSD_LOW_HZ
            )
            &
            (
                np.fft.rfftfreq(
                    STFT_PSD_N_FFT,
                    d=1.0 / sample_rate
                )
                <= upper_frequency
            )
        )
    )

    return {
        "n_fft":
            float(STFT_PSD_N_FFT),

        "hop_length":
            float(STFT_PSD_HOP_LENGTH),

        "frequency_resolution_hz":
            float(frequency_resolution),

        "total_frequency_bins":
            float(frequency_bins),

        "fingerprint_low_hz":
            float(STFT_PSD_LOW_HZ),

        "fingerprint_high_hz":
            float(upper_frequency),

        "fingerprint_dimensions":
            float(selected_bins),
    }