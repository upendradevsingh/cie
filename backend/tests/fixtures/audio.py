"""Generate minimal valid WAV files for testing.

Creates properly-formatted WAV files with valid headers and tiny audio data
so that file-type validation and upload tests work correctly.
"""

import os
import struct
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "audio"


def create_dummy_wav(path: str | Path, duration_seconds: float = 1.0, sample_rate: int = 8000) -> Path:
    """Create a minimal valid WAV file.

    Parameters
    ----------
    path:
        Output file path.
    duration_seconds:
        Duration of the audio in seconds.
    sample_rate:
        Sample rate in Hz.

    Returns
    -------
    Path
        The path to the created file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    num_samples = int(sample_rate * duration_seconds)
    data_size = num_samples * block_align

    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))  # chunk size
        f.write(b"WAVE")

        # fmt sub-chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # sub-chunk size
        f.write(struct.pack("<H", 1))   # audio format (PCM)
        f.write(struct.pack("<H", num_channels))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", byte_rate))
        f.write(struct.pack("<H", block_align))
        f.write(struct.pack("<H", bits_per_sample))

        # data sub-chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        # Write silence (zeros)
        f.write(b"\x00" * data_size)

    return path


def create_dummy_mp3(path: str | Path) -> Path:
    """Create a minimal file with an MP3-like header for testing.

    This creates a tiny file with a valid MP3 sync word so it passes
    basic format detection, but is not a valid playable MP3.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # MPEG 1, Layer 3, 128kbps, 44100 Hz, stereo
    # Sync word: 0xFF 0xFB
    mp3_frame_header = bytes([
        0xFF, 0xFB,  # sync word + MPEG1, Layer3
        0x90, 0x00,  # 128kbps, 44100Hz, padding=0
    ])
    # Pad with zeros to simulate frame data (417 bytes for 128kbps)
    frame_data = b"\x00" * 413

    with open(path, "wb") as f:
        f.write(mp3_frame_header + frame_data)

    return path


def ensure_dummy_audio_files() -> dict:
    """Create all dummy audio files and return a dict of paths."""
    files = {}
    files["hot_wav"] = create_dummy_wav(FIXTURES_DIR / "test_call_hot.wav")
    files["warm_wav"] = create_dummy_wav(FIXTURES_DIR / "test_call_warm.wav")
    files["cold_wav"] = create_dummy_wav(FIXTURES_DIR / "test_call_cold.wav")
    files["hinglish_wav"] = create_dummy_wav(FIXTURES_DIR / "test_call_hinglish.wav")
    files["test_mp3"] = create_dummy_mp3(FIXTURES_DIR / "test_call.mp3")
    return files
