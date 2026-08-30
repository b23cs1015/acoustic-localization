from pathlib import Path
from typing import Tuple

import librosa
import numpy as np
import soundfile as sf


def load_audio(
    path: Path,
    target_sample_rate: int = 48000,
) -> Tuple[np.ndarray, int]:

    audio, sample_rate = librosa.load(
        path,
        sr=target_sample_rate,
        mono=True,
    )

    audio = audio.astype(
        np.float32
    )

    return audio, sample_rate


def normalize_audio(
    audio: np.ndarray,
) -> np.ndarray:

    peak = np.max(
        np.abs(audio)
    )

    if peak <= 0:
        return audio

    return audio / peak