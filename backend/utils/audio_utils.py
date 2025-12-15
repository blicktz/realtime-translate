"""
Audio processing utilities for format conversion and analysis.
"""

import numpy as np
from typing import Tuple, Optional
import io
import wave


def pcm_to_float32(pcm_data: bytes, channels: int = 1) -> np.ndarray:
    """
    Convert PCM16 audio data to float32 numpy array.

    Args:
        pcm_data: Raw PCM16 audio bytes
        channels: Number of audio channels (1 for mono, 2 for stereo)

    Returns:
        Float32 numpy array normalized to [-1.0, 1.0]
    """
    # Convert bytes to int16 array
    audio_int16 = np.frombuffer(pcm_data, dtype=np.int16)

    # Reshape for multi-channel audio
    if channels > 1:
        audio_int16 = audio_int16.reshape(-1, channels)

    # Convert to float32 and normalize to [-1.0, 1.0]
    audio_float32 = audio_int16.astype(np.float32) / 32768.0

    return audio_float32


def float32_to_pcm(audio_float32: np.ndarray) -> bytes:
    """
    Convert float32 numpy array to PCM16 bytes.

    Args:
        audio_float32: Float32 numpy array normalized to [-1.0, 1.0]

    Returns:
        Raw PCM16 audio bytes
    """
    # Clip to valid range
    audio_float32 = np.clip(audio_float32, -1.0, 1.0)

    # Convert to int16
    audio_int16 = (audio_float32 * 32767).astype(np.int16)

    return audio_int16.tobytes()


def calculate_audio_level(audio_data: np.ndarray) -> float:
    """
    Calculate RMS audio level for visualization.

    Args:
        audio_data: Float32 audio samples

    Returns:
        RMS level normalized to [0.0, 1.0]
    """
    if len(audio_data) == 0:
        return 0.0

    # Calculate RMS (Root Mean Square)
    rms = np.sqrt(np.mean(audio_data ** 2))

    # Normalize to [0, 1] range
    # Typical speech RMS is around 0.1-0.3, so we scale accordingly
    normalized_level = min(rms * 3.0, 1.0)

    return float(normalized_level)


def detect_silence(audio_data: np.ndarray, threshold: float = 0.02) -> bool:
    """
    Detect if audio data is silence.

    Args:
        audio_data: Float32 audio samples
        threshold: RMS threshold below which audio is considered silence

    Returns:
        True if audio is silence, False otherwise
    """
    if len(audio_data) == 0:
        return True

    rms = np.sqrt(np.mean(audio_data ** 2))
    return rms < threshold


def resample_audio(
    audio_data: np.ndarray,
    orig_sample_rate: int,
    target_sample_rate: int
) -> np.ndarray:
    """
    Resample audio data to a different sample rate.

    Args:
        audio_data: Float32 audio samples
        orig_sample_rate: Original sample rate in Hz
        target_sample_rate: Target sample rate in Hz

    Returns:
        Resampled audio data
    """
    if orig_sample_rate == target_sample_rate:
        return audio_data

    # Simple linear interpolation resampling
    duration = len(audio_data) / orig_sample_rate
    target_length = int(duration * target_sample_rate)

    # Create indices for interpolation
    orig_indices = np.linspace(0, len(audio_data) - 1, len(audio_data))
    target_indices = np.linspace(0, len(audio_data) - 1, target_length)

    # Interpolate
    resampled = np.interp(target_indices, orig_indices, audio_data)

    return resampled


def create_wav_header(
    sample_rate: int,
    channels: int,
    sample_width: int,
    num_frames: int
) -> bytes:
    """
    Create WAV file header.

    Args:
        sample_rate: Sample rate in Hz
        channels: Number of audio channels
        sample_width: Bytes per sample (2 for PCM16)
        num_frames: Number of audio frames

    Returns:
        WAV header bytes
    """
    wav_io = io.BytesIO()

    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.setnframes(num_frames)

    wav_io.seek(0)
    header = wav_io.read(44)  # WAV header is 44 bytes

    return header


def extract_audio_features(audio_data: np.ndarray) -> dict:
    """
    Extract basic audio features for quality monitoring.

    Args:
        audio_data: Float32 audio samples

    Returns:
        Dictionary of audio features
    """
    if len(audio_data) == 0:
        return {
            "rms": 0.0,
            "peak": 0.0,
            "zero_crossings": 0,
            "duration_ms": 0.0
        }

    rms = float(np.sqrt(np.mean(audio_data ** 2)))
    peak = float(np.max(np.abs(audio_data)))

    # Zero crossings (indicator of speech vs noise)
    zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_data))))

    return {
        "rms": rms,
        "peak": peak,
        "zero_crossings": int(zero_crossings),
        "duration_ms": len(audio_data) / 16.0  # Assuming 16kHz
    }


def apply_gain(audio_data: np.ndarray, gain_db: float) -> np.ndarray:
    """
    Apply gain to audio data.

    Args:
        audio_data: Float32 audio samples
        gain_db: Gain in decibels

    Returns:
        Audio data with applied gain
    """
    # Convert dB to linear gain
    linear_gain = 10 ** (gain_db / 20.0)

    # Apply gain and clip to valid range
    gained_audio = audio_data * linear_gain
    gained_audio = np.clip(gained_audio, -1.0, 1.0)

    return gained_audio
